import discord
import yt_dlp
import logging
import asyncio
from database import add_to_queue, get_queue, remove_from_queue

async def play_song(ctx, url, queues):
    guild_id = str(ctx.guild.id)
    if guild_id not in queues:
        queues[guild_id] = []

    ydl_opts = {
        'format': 'bestaudio[acodec=mp3]/bestaudio',
        'noplaylist': True,
        'cachedir': r'f:\yoombot\yt_dlp_cache',
        'socket_timeout': 10,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            title = info.get('title', 'Unknown')
            queues[guild_id].append((url, audio_url, title))
            add_to_queue(guild_id, url, audio_url, title)
            await ctx.send(f'Đã thêm vào queue: {title}')
            logging.info(f"Added to queue: {title} for guild {guild_id}")
    except Exception as e:
        await ctx.send(f'Lỗi khi thêm {url} vào queue: {e}')
        logging.error(f"Error adding {url} to queue: {e}")
        return False
    return True

async def play_next(ctx, voice_client, queues, bot):
    guild_id = str(ctx.guild.id)
    queue = queues.get(guild_id, [])
    if len(queue) == 0:
        return
    url, audio_url, title = queue.pop(0)
    remove_from_queue(guild_id, 0)
    try:
        ffmpeg_options = {
            'options': '-reconnect 1 -reconnect_streamed 1 -bufsize 64k'
        }
        def after_playing(error):
            if error:
                print(f'Lỗi: {error}')
                logging.error(f"Playback error: {error}")
            bot.loop.call_soon_threadsafe(asyncio.create_task, play_next(ctx, voice_client, queues, bot))
        voice_client.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options), after=after_playing)
        await ctx.send(f'Đang phát: {title}')
        logging.info(f"Playing: {title} for guild {guild_id}")
    except Exception as e:
        await ctx.send(f'Lỗi khi phát {title}: {e}')
        logging.error(f"Error playing {title}: {e}")
        await play_next(ctx, voice_client, queues, bot)