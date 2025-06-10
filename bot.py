import discord
from discord import app_commands
from discord.ext import commands
import requests
import json
import logging
import asyncio
import yt_dlp
from config import BOT_TOKEN, GROQ_API_KEY, CHANNEL_ID, WELCOME_CHANNEL_ID
from database import init_db, add_message, get_history, get_queue, clear_queue
from music_player import play_song, play_playlist, play_next, get_progress_bar

# Set up logging to local file
logging.basicConfig(filename=r'./data/bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Discord bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store music queues in memory (synced with database)
queues = {}
loop_status = {}  # Để theo dõi trạng thái lặp lại

def get_groq_response(channel_id, message):
    history = get_history(channel_id)
    history.append({"role": "user", "content": message})
    full_history = [{"role": "system", "content": "You are a helpful assistant."}] + history
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": full_history,
        "max_tokens": 8192,
        "stream": False
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        api_response = response.json()["choices"][0]["message"]["content"]
        add_message(channel_id, None, "assistant", api_response)
        return api_response
    except requests.exceptions.RequestException as e:
        logging.error(f"Groq API error: {str(e)}")
        return f"Error calling Groq API: {str(e)}"

async def safe_voice_connect(ctx, timeout=10, retries=3):
    """Safely connect to voice channel with retries and timeout handling"""
    if ctx.author.voice is None:
        await ctx.send('❌ Bạn chưa ở trong kênh voice.')
        return None
    
    channel = ctx.author.voice.channel
    
    if ctx.voice_client is not None:
        if ctx.voice_client.channel == channel:
            return ctx.voice_client
        else:
            try:
                await ctx.voice_client.move_to(channel)
                return ctx.voice_client
            except Exception as e:
                logging.error(f"Error moving to voice channel: {e}")
                await ctx.voice_client.disconnect()
    
    for attempt in range(retries):
        try:
            await ctx.send(f'🔄 Đang kết nối đến kênh voice... (Lần thử {attempt + 1}/{retries})')
            voice_client = await channel.connect(timeout=timeout, reconnect=True, self_deaf=True)
            await ctx.send(f'✅ Đã kết nối đến kênh voice: **{channel.name}**')
            logging.info(f"Successfully connected to voice channel {channel.name} on attempt {attempt + 1}")
            return voice_client
        except asyncio.TimeoutError:
            logging.warning(f"Voice connection timeout on attempt {attempt + 1}")
            if attempt < retries - 1:
                await ctx.send(f'⏰ Kết nối bị timeout, đang thử lại...')
                await asyncio.sleep(2)
            else:
                await ctx.send('❌ Không thể kết nối đến kênh voice sau nhiều lần thử. Vui lòng thử lại sau.')
        except Exception as e:
            logging.error(f"Voice connection error on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                await ctx.send(f'❌ Lỗi kết nối, đang thử lại...')
                await asyncio.sleep(2)
            else:
                await ctx.send(f'❌ Không thể kết nối đến kênh voice: {str(e)}')
    
    return None

@bot.event
async def on_ready():
    print(f'{bot.user} đã kết nối với Discord!')
    init_db()
    for guild in bot.guilds:
        guild_id = str(guild.id)
        queues[guild_id] = get_queue(guild_id)
    await bot.tree.sync()  # Đồng bộ slash commands
    logging.info("Bot started, databases initialized, queues loaded, and slash commands synced")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.id == CHANNEL_ID:
        add_message(message.channel.id, message.id, "user", message.content)
        response = get_groq_response(message.channel.id, message.content)
        if len(response) <= 2000:
            await message.channel.send(response)
        else:
            chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
            for chunk in chunks:
                await message.channel.send(chunk)
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        await channel.send(f'Chào mừng {member.mention} đến với server!')
        logging.info(f"Welcome message sent for {member.name}")

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user:
        return
    
    if before.channel and bot.user in before.channel.members:
        human_members = [m for m in before.channel.members if not m.bot]
        if len(human_members) == 0:
            voice_client = discord.utils.get(bot.voice_clients, guild=before.channel.guild)
            if voice_client:
                await asyncio.sleep(30)
                human_members = [m for m in before.channel.members if not m.bot]
                if len(human_members) == 0:
                    await voice_client.disconnect()
                    logging.info(f"Disconnected from empty voice channel in guild {before.channel.guild.id}")

# Slash Commands
@bot.tree.command(name="play", description="Phát nhạc từ URL YouTube/Spotify hoặc tìm kiếm theo từ khóa")
@app_commands.describe(query="Tên bài hát, URL YouTube hoặc Spotify")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    ctx = await bot.get_context(interaction)
    voice_client = await safe_voice_connect(ctx)
    if voice_client is None:
        await interaction.followup.send("❌ Không thể kết nối voice channel!")
        return
    
    try:
        if "list=" in query or "playlist" in query.lower():
            if await play_playlist(ctx, query, queues):
                if not voice_client.is_playing():
                    await play_next(ctx, voice_client, queues, bot)
                await interaction.followup.send("🎶 Đã thêm playlist vào queue!")
        else:
            if await play_song(ctx, query, queues):
                if not voice_client.is_playing():
                    await play_next(ctx, voice_client, queues, bot)
                await interaction.followup.send("🎵 Đã thêm bài hát vào queue!")
    except Exception as e:
        await interaction.followup.send(f'❌ Lỗi khi phát nhạc: {str(e)}')
        logging.error(f"Error in play command: {e}")

@bot.tree.command(name="skip", description="Bỏ qua bài hát hiện tại")
async def skip(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_playing():
        await interaction.response.send_message('❌ Không có bài hát nào đang phát.')
        return
    voice_client.stop()
    await interaction.response.send_message('⏭️ Đã bỏ qua bài hát hiện tại.')
    logging.info(f"Skipped current song in guild {ctx.guild.id}")

@bot.tree.command(name="pause", description="Tạm dừng bài hát đang phát")
async def pause(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_playing():
        await interaction.response.send_message('❌ Không có bài hát nào đang phát để tạm dừng.')
        return
    voice_client.pause()
    await interaction.response.send_message('⏸️ Đã tạm dừng bài hát.')
    logging.info(f"Paused music in guild {ctx.guild.id}")

@bot.tree.command(name="resume", description="Tiếp tục phát bài hát đã tạm dừng")
async def resume(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_paused():
        await interaction.response.send_message('❌ Không có bài hát nào đang tạm dừng để tiếp tục.')
        return
    voice_client.resume()
    await interaction.response.send_message('▶️ Đã tiếp tục phát bài hát.')
    logging.info(f"Resumed music in guild {ctx.guild.id}")

@bot.tree.command(name="queue", description="Hiển thị danh sách queue nhạc hiện tại")
async def show_queue(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    guild_id = str(ctx.guild.id)
    queue = queues.get(guild_id, [])
    if len(queue) == 0:
        await interaction.response.send_message('📋 Queue hiện tại đang trống.')
    else:
        queue_list = []
        for i, (url, audio_url, title, duration) in enumerate(queue):
            duration_str = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else "Unknown"
            status = "🎵 **Đang phát**" if i == 0 else f"{i+1}."
            queue_list.append(f'{status} **{title}** ({duration_str})')
        
        result = f'🎵 **Danh sách queue ({len(queue)} bài):**\n\n' + '\n'.join(queue_list)
        await interaction.response.send_message(result[:2000])
        logging.info(f"Displayed queue for guild {guild_id}")

@bot.tree.command(name="now", description="Hiển thị bài hát đang phát")
async def now_playing(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_playing():
        await interaction.response.send_message('❌ Không có bài hát nào đang phát.')
        return
    
    guild_id = str(ctx.guild.id)
    queue = queues.get(guild_id, [])
    if queue:
        url, _, title, duration = queue[0]
        duration_str = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else "Unknown"
        await interaction.response.send_message(f'🎵 **Đang phát:** {title} ({duration_str})')
    else:
        await interaction.response.send_message('🎵 Đang phát nhạc.')

@bot.tree.command(name="stop", description="Dừng phát nhạc và xóa queue")
async def stop(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    voice_client = ctx.voice_client
    if voice_client is None:
        await interaction.response.send_message('❌ Chưa kết nối với kênh voice')
        return
    
    voice_client.stop()
    guild_id = str(ctx.guild.id)
    clear_queue(guild_id)
    queues[guild_id] = []
    loop_status[guild_id] = {"mode": "off", "current_song": None, "start_time": None}
    await interaction.response.send_message('⏹️ Đã dừng nhạc và xóa queue.')
    logging.info(f"Stopped music and cleared queue for guild {ctx.guild.id}")

@bot.tree.command(name="leave", description="Rời khỏi kênh voice")
async def leave(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    voice_client = ctx.voice_client
    if voice_client is None:
        await interaction.response.send_message('❌ Chưa kết nối với kênh voice')
        return
    
    clear_queue(str(ctx.guild.id))
    queues[str(ctx.guild.id)] = []
    loop_status[str(ctx.guild.id)] = {"mode": "off", "current_song": None, "start_time": None}
    await voice_client.disconnect()
    await interaction.response.send_message('👋 Đã rời khỏi kênh voice.')
    logging.info(f"Left voice channel for guild {ctx.guild.id}")

@bot.tree.command(name="loop", description="Bật/tắt chế độ lặp lại bài hát hoặc queue")
@app_commands.describe(mode="Chọn chế độ: off, song, queue")
@app_commands.choices(mode=[
    app_commands.Choice(name="Tắt", value="off"),
    app_commands.Choice(name="Lặp bài hát", value="song"),
    app_commands.Choice(name="Lặp queue", value="queue")
])
async def loop(interaction: discord.Interaction, mode: str):
    ctx = await bot.get_context(interaction)
    guild_id = str(ctx.guild.id)
    
    if mode not in ["off", "song", "queue"]:
        await interaction.response.send_message("❌ Chế độ không hợp lệ! Chọn: off, song, queue")
        return
    
    loop_status[guild_id] = loop_status.get(guild_id, {})
    loop_status[guild_id]["mode"] = mode
    
    if mode == "off":
        await interaction.response.send_message("🔁 Đã tắt chế độ lặp lại.")
    elif mode == "song":
        await interaction.response.send_message("🔂 Đã bật chế độ lặp bài hát hiện tại.")
    elif mode == "queue":
        await interaction.response.send_message("🔁 Đã bật chế độ lặp toàn bộ queue.")
    
    logging.info(f"Set loop mode to {mode} for guild {guild_id}")

@bot.tree.command(name="progress", description="Hiển thị thanh tiến trình bài hát đang phát")
async def progress(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    progress_text = await get_progress_bar(ctx, queues)
    await interaction.response.send_message(progress_text)

# Prefix Commands (Restored)
@bot.command(name='play', help='Phát nhạc từ URL YouTube hoặc tìm kiếm theo từ khóa')
async def play_prefix(ctx, *, query: str):
    voice_client = await safe_voice_connect(ctx)
    if voice_client is None:
        await ctx.send("❌ Không thể kết nối voice channel!")
        return
    
    try:
        if "list=" in query or "playlist" in query.lower():
            if await play_playlist(ctx, query, queues):
                if not voice_client.is_playing():
                    await play_next(ctx, voice_client, queues, bot)
                await ctx.send("🎶 Đã thêm playlist vào queue!")
        else:
            if await play_song(ctx, query, queues):
                if not voice_client.is_playing():
                    await play_next(ctx, voice_client, queues, bot)
                await ctx.send("🎵 Đã thêm bài hát vào queue!")
    except Exception as e:
        await ctx.send(f'❌ Lỗi khi phát nhạc: {str(e)}')
        logging.error(f"Error in play command: {e}")

@bot.command(name='skip', help='Bỏ qua bài hát hiện tại')
async def skip_prefix(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_playing():
        await ctx.send('❌ Không có bài hát nào đang phát.')
        return
    voice_client.stop()
    await ctx.send('⏭️ Đã bỏ qua bài hát hiện tại.')
    logging.info(f"Skipped current song in guild {ctx.guild.id}")

@bot.command(name='pause', help='Tạm dừng bài hát đang phát')
async def pause_prefix(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_playing():
        await ctx.send('❌ Không có bài hát nào đang phát để tạm dừng.')
        return
    voice_client.pause()
    await ctx.send('⏸️ Đã tạm dừng bài hát.')
    logging.info(f"Paused music in guild {ctx.guild.id}")

@bot.command(name='resume', help='Tiếp tục phát bài hát đã tạm dừng')
async def resume_prefix(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_paused():
        await ctx.send('❌ Không có bài hát nào đang tạm dừng để tiếp tục.')
        return
    voice_client.resume()
    await ctx.send('▶️ Đã tiếp tục phát bài hát.')
    logging.info(f"Resumed music in guild {ctx.guild.id}")

@bot.command(name='queue', help='Hiển thị danh sách queue nhạc hiện tại')
async def show_queue_prefix(ctx):
    guild_id = str(ctx.guild.id)
    queue = queues.get(guild_id, [])
    if len(queue) == 0:
        await ctx.send('📋 Queue hiện tại đang trống.')
    else:
        queue_list = []
        for i, (url, audio_url, title, duration) in enumerate(queue):
            duration_str = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else "Unknown"
            status = "🎵 **Đang phát**" if i == 0 else f"{i+1}."
            queue_list.append(f'{status} **{title}** ({duration_str})')
        
        result = f'🎵 **Danh sách queue ({len(queue)} bài):**\n\n' + '\n'.join(queue_list)
        await ctx.send(result[:2000])
        logging.info(f"Displayed queue for guild {guild_id}")

@bot.command(name='now', help='Hiển thị bài hát đang phát')
async def now_playing_prefix(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_playing():
        await ctx.send('❌ Không có bài hát nào đang phát.')
        return
    
    guild_id = str(ctx.guild.id)
    queue = queues.get(guild_id, [])
    if queue:
        url, _, title, duration = queue[0]
        duration_str = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else "Unknown"
        await ctx.send(f'🎵 **Đang phát:** {title} ({duration_str})')
    else:
        await ctx.send('🎵 Đang phát nhạc.')

@bot.command(name='stop', help='Dừng phát nhạc và xóa queue')
async def stop_prefix(ctx):
    voice_client = ctx.voice_client
    if voice_client is None:
        await ctx.send('❌ Chưa kết nối với kênh voice')
        return
    
    voice_client.stop()
    guild_id = str(ctx.guild.id)
    clear_queue(guild_id)
    queues[guild_id] = []
    loop_status[guild_id] = {"mode": "off", "current_song": None, "start_time": None}
    await ctx.send('⏹️ Đã dừng nhạc và xóa queue.')
    logging.info(f"Stopped music and cleared queue for guild {ctx.guild.id}")

@bot.command(name='leave', help='Rời khỏi kênh voice')
async def leave_prefix(ctx):
    voice_client = ctx.voice_client
    if voice_client is None:
        await ctx.send('❌ Chưa kết nối với kênh voice')
        return
    
    clear_queue(str(ctx.guild.id))
    queues[str(ctx.guild.id)] = []
    loop_status[str(ctx.guild.id)] = {"mode": "off", "current_song": None, "start_time": None}
    await voice_client.disconnect()
    await ctx.send('👋 Đã rời khỏi kênh voice.')
    logging.info(f"Left voice channel for guild {ctx.guild.id}")

@bot.command(name='loop', help='Bật/tắt chế độ lặp lại bài hát hoặc queue (off, song, queue)')
async def loop_prefix(ctx, mode: str):
    guild_id = str(ctx.guild.id)
    
    if mode not in ["off", "song", "queue"]:
        await ctx.send("❌ Chế độ không hợp lệ! Chọn: off, song, queue")
        return
    
    loop_status[guild_id] = loop_status.get(guild_id, {})
    loop_status[guild_id]["mode"] = mode
    
    if mode == "off":
        await ctx.send("🔁 Đã tắt chế độ lặp lại.")
    elif mode == "song":
        await ctx.send("🔂 Đã bật chế độ lặp bài hát hiện tại.")
    elif mode == "queue":
        await ctx.send("🔁 Đã bật chế độ lặp toàn bộ queue.")
    
    logging.info(f"Set loop mode to {mode} for guild {guild_id}")

@bot.command(name='progress', help='Hiển thị thanh tiến trình bài hát đang phát')
async def progress_prefix(ctx):
    progress_text = await get_progress_bar(ctx, queues)
    await ctx.send(progress_text)

@bot.command(name='join', help='Tham gia kênh voice của người dùng')
async def join(ctx):
    voice_client = await safe_voice_connect(ctx)
    if voice_client:
        logging.info(f"Joined voice channel via join command")

@bot.command(name='search', help='Tìm kiếm bài hát mà không phát (để debug)')
async def search(ctx, *, query: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
    }
    
    search_query = f"ytsearch5:{query}"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            
            if 'entries' in info and info['entries']:
                results = []
                for i, entry in enumerate(info['entries'][:5]):
                    if entry:
                        title = entry.get('title', 'Unknown')
                        uploader = entry.get('uploader', 'Unknown')
                        duration = entry.get('duration', 0)
                        duration_str = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else "Unknown"
                        results.append(f"{i+1}. **{title}**\n   👤 {uploader} | ⏱️ {duration_str}")
                
                result_text = f"🔍 Kết quả tìm kiếm cho '{query}':\n\n" + "\n\n".join(results)
                await ctx.send(result_text[:2000])
            else:
                await ctx.send(f"❌ Không tìm thấy kết quả cho: '{query}'")
                
    except Exception as e:
        await ctx.send(f"❌ Lỗi khi tìm kiếm: {str(e)}")
        logging.error(f"Search error for '{query}': {e}")

@bot.command(name='debug', help='Hiển thị thông tin debug')
async def debug(ctx):
    guild_id = str(ctx.guild.id)
    voice_client = ctx.voice_client
    queue = queues.get(guild_id, [])
    
    debug_info = f"""
**🔧 Thông tin Debug:**
📍 Guild ID: {guild_id}
🔊 Voice Client: {'Connected' if voice_client and voice_client.is_connected() else 'Disconnected'}
🎵 Is Playing: {'Yes' if voice_client and voice_client.is_playing() else 'No'}
⏸️ Is Paused: {'Yes' if voice_client and voice_client.is_paused() else 'No'}
📋 Queue Length: {len(queue)}
💾 Memory Queue: {len(queues.get(guild_id, []))}
🌐 Voice Channel: {voice_client.channel.name if voice_client and voice_client.channel else 'None'}
🔁 Loop Mode: {loop_status.get(guild_id, {}).get('mode', 'off')}
    """
    await ctx.send(debug_info)

@bot.command(name='ffmpeg_test', help='Test FFmpeg')
async def ffmpeg_test(ctx):
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        await ctx.send(f"FFmpeg version: {result.stdout[:500]}")
    except Exception as e:
        await ctx.send(f"FFmpeg error: {e}")

@bot.command(name='test_stream', help='Test stream URL cho debug')
async def test_stream(ctx, *, query: str):
    from music_player import get_fresh_audio_url, test_stream_url
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }
    
    is_url = query.startswith(('http://', 'https://', 'www.'))
    if not is_url:
        query = f"ytsearch1:{query}"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            
            if 'entries' in info and info['entries']:
                entry = info['entries'][0]
                if entry:
                    video_url = entry['webpage_url']
                    title = entry.get('title', 'Unknown')
            elif 'webpage_url' in info:
                video_url = info['webpage_url']
                title = info.get('title', 'Unknown')
            else:
                await ctx.send('❌ Không tìm thấy video')
                return
        
        await ctx.send(f'🔍 Testing stream cho: **{title}**')
        
        stream_url = await get_fresh_audio_url(video_url)
        if not stream_url:
            await ctx.send('❌ Không lấy được stream URL')
            return
        
        await ctx.send(f'📡 Stream URL: `{stream_url[:100]}...`')
        await test_stream_url(stream_url, ctx)
        
    except Exception as e:
        await ctx.send(f'❌ Lỗi test stream: {str(e)}')

@bot.command(name='voice_debug', help='Debug thông tin voice connection')
async def voice_debug(ctx):
    vc = ctx.voice_client
    
    debug_info = []
    debug_info.append("🔧 **Voice Connection Debug:**")
    debug_info.append(f"📍 Guild: {ctx.guild.name} ({ctx.guild.id})")
    
    if vc:
        debug_info.append(f"🔊 Connected: {vc.is_connected()}")
        debug_info.append(f"🎵 Playing: {vc.is_playing()}")
        debug_info.append(f"⏸️ Paused: {vc.is_paused()}")
        debug_info.append(f"🌐 Channel: {vc.channel.name if vc.channel else 'None'}")
        debug_info.append(f"🔗 Endpoint: {vc.endpoint}")
        debug_info.append(f"📶 Average latency: {vc.average_latency:.2f}ms")
        debug_info.append(f"🏓 Latency: {vc.latency:.2f}ms")
    else:
        debug_info.append("❌ No voice client")
    
    if ctx.author.voice:
        debug_info.append(f"👤 User channel: {ctx.author.voice.channel.name}")
        debug_info.append(f"👥 Members in channel: {len(ctx.author.voice.channel.members)}")
    else:
        debug_info.append("👤 User not in voice channel")
    
    await ctx.send('\n'.join(debug_info))

@bot.command(name='force_reconnect', help='Buộc kết nối lại voice')
async def force_reconnect(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await asyncio.sleep(2)
    
    voice_client = await safe_voice_connect(ctx)
    if voice_client:
        await ctx.send('✅ Đã kết nối lại voice thành công')
    else:
        await ctx.send('❌ Không thể kết nối lại voice')

@bot.command(name='clear_cache', help='Xóa cache yt-dlp')
async def clear_cache(ctx):
    import shutil
    import os
    
    cache_dir = r'./data/yt_dlp_cache'
    try:
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir, exist_ok=True)
            await ctx.send('✅ Đã xóa cache yt-dlp')
        else:
            await ctx.send('📁 Cache không tồn tại')
    except Exception as e:
        await ctx.send(f'❌ Lỗi xóa cache: {str(e)}')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('❌ Thiếu tham số bắt buộc. Sử dụng `!help` để xem hướng dẫn.')
    elif isinstance(error, commands.BadArgument):
        await ctx.send('❌ Tham số không hợp lệ. Vui lòng kiểm tra lại.')
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send('❌ Lệnh không tồn tại. Sử dụng `!help` để xem danh sách lệnh.')
    elif isinstance(error, commands.CommandInvokeError):
        if "TimeoutError" in str(error):
            await ctx.send('⏰ Lệnh bị timeout. Vui lòng thử lại sau.')
        else:
            await ctx.send(f'❌ Đã xảy ra lỗi khi thực hiện lệnh.')
        logging.error(f"Command error: {error}")
    else:
        await ctx.send(f'❌ Đã xảy ra lỗi không xác định.')
        logging.error(f"Unhandled error: {error}")

# Run the bot
bot.run(BOT_TOKEN)