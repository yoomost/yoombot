import discord
import yt_dlp
import logging
import asyncio
from database import add_to_queue, get_queue, remove_from_queue

async def play_song(ctx, query, queues):
    guild_id = str(ctx.guild.id)
    if guild_id not in queues:
        queues[guild_id] = []

    ydl_opts = {
        'format': 'bestaudio[acodec=mp3]/bestaudio',
        'cachedir': r'.\yt_dlp_cache',
        'socket_timeout': 10,
        'default_search': 'ytsearch',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                for entry in info['entries']:
                    if entry:
                        url = entry['webpage_url']
                        audio_url = entry['url']
                        title = entry.get('title', 'Unknown')
                        duration = entry.get('duration', 0)
                        queues[guild_id].append((url, audio_url, title, duration))
                        add_to_queue(guild_id, url, audio_url, title)
                        await ctx.send(f'Đã thêm vào queue: {title} ({duration // 60}:{duration % 60:02d})')
                        logging.info(f"Added to queue: {title} (duration: {duration}s) for guild {guild_id}")
            else:
                url = info['webpage_url']
                audio_url = info['url']
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                queues[guild_id].append((url, audio_url, title, duration))
                add_to_queue(guild_id, url, audio_url, title)
                await ctx.send(f'Đã thêm vào queue: {title} ({duration // 60}:{duration % 60:02d})')
                logging.info(f"Added to queue: {title} (duration: {duration}s) for guild {guild_id}")
    except Exception as e:
        await ctx.send(f'Lỗi khi thêm "{query}" vào queue: {e}')
        logging.error(f"Error adding {query} to queue: {e}")
        return False
    return True

async def play_next(ctx, voice_client, queues, bot):
    guild_id = str(ctx.guild.id)
    # Kiểm tra nếu bot không kết nối hoặc đã mất kết nối
    if voice_client is None or not voice_client.is_connected():
        if ctx.author.voice:
            try:
                voice_client = await ctx.author.voice.channel.connect()
                logging.info(f"Reconnected to voice channel for guild {guild_id}")
            except Exception as e:
                await ctx.send("Không thể kết nối lại với kênh voice. Vui lòng kiểm tra kết nối hoặc thử lại.")
                logging.error(f"Failed to reconnect to voice channel for guild {guild_id}: {e}")
                return
        else:
            await ctx.send("Bạn cần ở trong kênh voice để bot có thể phát nhạc.")
            logging.warning(f"No user in voice channel for guild {guild_id}")
            return

    # Lấy queue của guild
    queue = queues.get(guild_id, [])
    if len(queue) == 0:
        await ctx.send("Queue đã hết. Thêm bài hát mới bằng lệnh !play.")
        logging.info(f"No songs left in queue for guild {guild_id}")
        return

    # Lấy bài hát tiếp theo từ queue
    url, audio_url, title, duration = queue.pop(0)
    remove_from_queue(guild_id, 0)

    try:
        # Cấu hình FFmpeg với các tùy chọn tối ưu
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -b:a 128k -acodec libopus'  # Bitrate 128kbps, sử dụng codec Opus
        }

        # Callback sau khi phát xong
        def after_playing(error):
            if error:
                print(f'Lỗi phát nhạc: {error}')
                logging.error(f"Playback error for {title} in guild {guild_id}: {error}")
            else:
                logging.info(f"Finished playing {title} (duration: {duration}s) in guild {guild_id}")
            # Lên lịch phát bài tiếp theo
            bot.loop.call_soon_threadsafe(asyncio.create_task, play_next(ctx, voice_client, queues, bot))

        # Phát bài hát
        voice_client.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options), after=after_playing)
        await ctx.send(f'Đang phát: {title} ({duration // 60}:{duration % 60:02d})')
        logging.info(f"Playing: {title} (duration: {duration}s) for guild {guild_id}")

    except Exception as e:
        await ctx.send(f'Lỗi khi phát {title}: {str(e)}')
        logging.error(f"Error playing {title} in guild {guild_id}: {e}")
        # Thử phát bài tiếp theo nếu có lỗi
        await play_next(ctx, voice_client, queues, bot)