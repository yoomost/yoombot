import discord
from discord.ext import commands
import requests
import json
import logging
import asyncio
from config import BOT_TOKEN, GROQ_API_KEY, CHANNEL_ID, WELCOME_CHANNEL_ID
from database import init_db, add_message, get_history, get_queue, clear_queue
from music_player import play_song, play_next

# Set up logging to local file
logging.basicConfig(filename=r'bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Discord bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store music queues in memory (synced with database)
queues = {}

def get_groq_response(channel_id, message):
    history = get_history(channel_id)
    history.append({"role": "user", "content": message})
    full_history = [{"role": "system", "content": "You are a helpful assistant. Keep responses concise, under 1500 characters."}] + history
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": full_history,
        "max_tokens": 1500,
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

@bot.event
async def on_ready():
    print(f'{bot.user} đã kết nối với Discord!')
    init_db()  # Initialize databases
    for guild in bot.guilds:
        guild_id = str(guild.id)
        queues[guild_id] = get_queue(guild_id)
    logging.info("Bot started, databases initialized, and queues loaded")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.id == CHANNEL_ID:
        add_message(message.channel.id, message.id, "user", message.content)
        response = get_groq_response(message.channel.id, message.content)
        if len(response) > 2000:
            response = response[:1997] + "..."
        await message.channel.send(response)
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        await channel.send(f'Chào mừng {member.mention} đến với server!')
        logging.info(f"Welcome message sent for {member.name}")

@bot.command(name='join', help='Tham gia kênh voice của người dùng')
async def join(ctx):
    if ctx.author.voice is None:
        await ctx.send('Bạn chưa ở trong kênh voice.')
        return
    channel = ctx.author.voice.channel
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()
    await ctx.send('Đã tham gia kênh voice.')
    logging.info(f"Joined voice channel {channel.name}")

@bot.command(name='play', help='Phát nhạc từ URL YouTube hoặc tìm kiếm theo từ khóa')
async def play(ctx, *, query: str):
    voice_client = ctx.voice_client
    if voice_client is None:
        if ctx.author.voice is None:
            await ctx.send("Bạn chưa ở trong kênh voice.")
            return
        else:
            voice_client = await ctx.author.voice.channel.connect()

    if await play_song(ctx, query, queues):
        if not voice_client.is_playing():
            await play_next(ctx, voice_client, queues, bot)

@bot.command(name='skip', help='Bỏ qua bài hát hiện tại')
async def skip(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_playing():
        await ctx.send('Không có bài hát nào đang phát.')
        return
    voice_client.stop()
    await ctx.send('Đã bỏ qua bài hát hiện tại.')
    logging.info(f"Skipped current song in guild {ctx.guild.id}")

@bot.command(name='pause', help='Tạm dừng bài hát đang phát')
async def pause(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_playing():
        await ctx.send('Không có bài hát nào đang phát để tạm dừng.')
        return
    voice_client.pause()
    await ctx.send('Đã tạm dừng bài hát.')
    logging.info(f"Paused music in guild {ctx.guild.id}")

@bot.command(name='resume', help='Tiếp tục phát bài hát đã tạm dừng')
async def resume(ctx):
    voice_client = ctx.voice_client
    if voice_client is None or not voice_client.is_paused():
        await ctx.send('Không có bài hát nào đang tạm dừng để tiếp tục.')
        return
    voice_client.resume()
    await ctx.send('Đã tiếp tục phát bài hát.')
    logging.info(f"Resumed music in guild {ctx.guild.id}")

@bot.command(name='queue', help='Hiển thị danh sách queue nhạc hiện tại')
async def show_queue(ctx):
    guild_id = str(ctx.guild.id)
    queue = queues.get(guild_id, [])
    if len(queue) == 0:
        await ctx.send('Queue hiện tại đang trống.')
    else:
        queue_list = '\n'.join([f'{i+1}. {title}' for i, (url, audio_url, title) in enumerate(queue)])
        await ctx.send(f'Danh sách queue:\n{queue_list}')
        logging.info(f"Displayed queue for guild {guild_id}")

@bot.command(name='stop', help='Dừng phát nhạc')
async def stop(ctx):
    voice_client = ctx.voice_client
    if voice_client is None:
        await ctx.send('Chưa kết nối với kênh voice')
        return
    voice_client.stop()
    await ctx.send('Đã dừng nhạc')
    logging.info(f"Stopped music for guild {ctx.guild.id}")

@bot.command(name='leave', help='Rời khỏi kênh voice')
async def leave(ctx):
    voice_client = ctx.voice_client
    if voice_client is None:
        await ctx.send('Chưa kết nối với kênh voice')
        return
    clear_queue(str(ctx.guild.id))
    queues[str(ctx.guild.id)] = []
    await voice_client.disconnect()
    await ctx.send('Đã rời khỏi kênh voice')
    logging.info(f"Left voice channel for guild {ctx.guild.id}")

# Run the bot
bot.run(BOT_TOKEN)