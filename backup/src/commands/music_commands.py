import discord
from discord import app_commands
from discord.ext import commands
import logging
from database import clear_queue
from src.music.player import play_song, play_playlist, play_next
from src.music.utils import get_progress_bar
from src.utils.helpers import safe_voice_connect

def setup_music_commands(bot, queues, loop_status):
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
                        await play_next(ctx, voice_client, queues, bot, loop_status)
                    await interaction.followup.send("🎶 Đã thêm playlist vào queue!")
            else:
                if await play_song(ctx, query, queues):
                    if not voice_client.is_playing():
                        await play_next(ctx, voice_client, queues, bot, loop_status)
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
        progress_text = await get_progress_bar(ctx, queues, loop_status)
        await interaction.response.send_message(progress_text)

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
                        await play_next(ctx, voice_client, queues, bot, loop_status)
                    await ctx.send("🎶 Đã thêm playlist vào queue!")
            else:
                if await play_song(ctx, query, queues):
                    if not voice_client.is_playing():
                        await play_next(ctx, voice_client, queues, bot, loop_status)
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
        progress_text = await get_progress_bar(ctx, queues, loop_status)
        await ctx.send(progress_text)

    @bot.command(name='join', help='Tham gia kênh voice của người dùng')
    async def join(ctx):
        voice_client = await safe_voice_connect(ctx)
        if voice_client:
            logging.info(f"Joined voice channel via join command")