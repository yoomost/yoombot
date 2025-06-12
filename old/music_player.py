import discord
import yt_dlp
import logging
import asyncio
import time
from database import add_to_queue, get_queue, remove_from_queue

# Dictionary để lưu trạng thái lặp lại (per guild)
loop_status = {}  # Format: {guild_id: {"mode": "off" | "song" | "queue", "current_song": (url, audio_url, title, duration), "start_time": timestamp}}

async def play_song(ctx, query, queues):
    guild_id = str(ctx.guild.id)
    if guild_id not in queues:
        queues[guild_id] = []

    # Kiểm tra xem query có phải là URL hay không
    is_url = query.startswith(('http://', 'https://', 'www.'))
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'cachedir': r'./data/yt_dlp_cache',
        'socket_timeout': 30,
        'quiet': True,
        'no_warnings': True,
        'extractaudio': True,
        'audioformat': 'webm',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'force_json': True,
        'extract_flat': False,
    }
    
    # Nếu không phải URL, thêm prefix tìm kiếm YouTube hoặc Spotify
    if not is_url:
        query = f"ytsearch1:{query}"
        ydl_opts['default_search'] = 'ytsearch1'
    else:
        ydl_opts['noplaylist'] = True

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            
            # Xử lý kết quả tìm kiếm
            if 'entries' in info and info['entries']:
                # Lấy kết quả đầu tiên từ tìm kiếm
                entry = info['entries'][0]
                if entry:
                    url = entry['webpage_url']
                    title = entry.get('title', 'Unknown')
                    duration = entry.get('duration', 0)
                    uploader = entry.get('uploader', 'Unknown')
                    
                    # Lưu thông tin cơ bản
                    queues[guild_id].append((url, None, title, duration))
                    add_to_queue(guild_id, url, "", title, duration)
                    
                    duration_str = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else "Unknown"
                    await ctx.send(f'🎵 Đã thêm vào queue:\n**{title}**\n⏱️ Thời lượng: {duration_str}\n👤 Kênh: {uploader}')
                    logging.info(f"Added to queue: {title} (duration: {duration}s) for guild {guild_id}")
                else:
                    await ctx.send(f'❌ Không tìm thấy kết quả cho: "{query}"')
                    return False
            elif 'webpage_url' in info:
                # Xử lý URL trực tiếp
                url = info['webpage_url']
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                uploader = info.get('uploader', 'Unknown')
                
                queues[guild_id].append((url, None, title, duration))
                add_to_queue(guild_id, url, "", title, duration)
                
                duration_str = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else "Unknown"
                await ctx.send(f'🎵 Đã thêm vào queue:\n**{title}**\n⏱️ Thời lượng: {duration_str}\n👤 Kênh: {uploader}')
                logging.info(f"Added to queue: {title} (duration: {duration}s) for guild {guild_id}")
            else:
                await ctx.send(f'❌ Không thể xử lý: "{query}"')
                return False
                
    except Exception as e:
        await ctx.send(f'❌ Lỗi khi thêm "{query}" vào queue: {str(e)}')
        logging.error(f"Error adding {query} to queue: {e}")
        return False
    return True

async def play_playlist(ctx, playlist_url, queues):
    guild_id = str(ctx.guild.id)
    if guild_id not in queues:
        queues[guild_id] = []

    # Cải thiện ydl_opts cho playlist
    ydl_opts = {
        'format': 'bestaudio/best',
        'cachedir': r'./data/yt_dlp_cache',
        'socket_timeout': 45,  # Tăng timeout cho playlist
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',  # Chỉ lấy metadata cơ bản
        'playlistend': 50,  # Giới hạn số lượng bài để tránh quá tải
        'retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': True,
        'ignoreerrors': True,  # Bỏ qua các video lỗi trong playlist
    }

    try:
        # Gửi thông báo đang xử lý
        processing_msg = await ctx.send("🔄 Đang xử lý playlist, vui lòng đợi...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            
            if 'entries' not in info or not info['entries']:
                await processing_msg.edit(content="❌ Không phải playlist hợp lệ hoặc playlist trống!")
                return False
            
            playlist_title = info.get('title', 'Unknown Playlist')
            total_entries = len([e for e in info['entries'] if e])  # Đếm entries hợp lệ
            
            await processing_msg.edit(content=f"📋 Đang thêm {total_entries} bài từ playlist: **{playlist_title}**")
            
            added_count = 0
            failed_count = 0
            
            # Xử lý từng bài trong playlist với batch processing
            batch_size = 5
            for i in range(0, len(info['entries']), batch_size):
                batch = info['entries'][i:i+batch_size]
                
                for entry in batch:
                    if not entry:
                        failed_count += 1
                        continue
                        
                    try:
                        # Xử lý các dạng URL khác nhau
                        if 'url' in entry:
                            url = entry['url']
                        elif 'webpage_url' in entry:
                            url = entry['webpage_url']
                        elif 'id' in entry:
                            # Tạo URL từ ID (chủ yếu cho YouTube)
                            url = f"https://www.youtube.com/watch?v={entry['id']}"
                        else:
                            logging.warning(f"No valid URL found for entry: {entry}")
                            failed_count += 1
                            continue
                        
                        title = entry.get('title', 'Unknown')
                        duration = entry.get('duration', 0) or 0
                        uploader = entry.get('uploader', 'Unknown')
                        
                        # Kiểm tra URL hợp lệ
                        if not url or not url.startswith(('http://', 'https://')):
                            logging.warning(f"Invalid URL for {title}: {url}")
                            failed_count += 1
                            continue
                        
                        queues[guild_id].append((url, None, title, duration))
                        add_to_queue(guild_id, url, "", title, duration)
                        added_count += 1
                        
                        duration_str = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else "Unknown"
                        logging.info(f"Added to queue from playlist: {title} (duration: {duration}s) for guild {guild_id}")
                        
                    except Exception as e:
                        logging.error(f"Error processing playlist entry {entry.get('title', 'Unknown')}: {e}")
                        failed_count += 1
                        continue
                
                # Cập nhật tiến trình sau mỗi batch
                if (i + batch_size) % 10 == 0 or (i + batch_size) >= len(info['entries']):
                    progress = min(i + batch_size, len(info['entries']))
                    await processing_msg.edit(content=f"📋 Đã xử lý {progress}/{len(info['entries'])} bài từ playlist: **{playlist_title}**")
                
                # Delay ngắn giữa các batch để tránh rate limit
                await asyncio.sleep(0.1)
            
            # Thông báo kết quả
            result_msg = f'🎶 Đã thêm **{added_count}** bài hát từ playlist: **{playlist_title}**'
            if failed_count > 0:
                result_msg += f'\n⚠️ {failed_count} bài không thể thêm (có thể do video bị hạn chế hoặc lỗi)'
            
            await processing_msg.edit(content=result_msg)
            
            if added_count > 0:
                return True
            else:
                await ctx.send("❌ Không thể thêm bài nào từ playlist này!")
                return False
                
    except Exception as e:
        error_msg = f'❌ Lỗi khi xử lý playlist: {str(e)}'
        await ctx.send(error_msg)
        logging.error(f"Playlist error: {e}")
        return False

async def get_fresh_audio_url(url):
    """Lấy URL âm thanh mới từ video URL để tránh hết hạn"""
    ydl_opts = {
        'format': 'bestaudio[abr<=128]/bestaudio/best[height<=480]',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 20,  # Giảm timeout để tránh block
        'force_json': True,
        'extract_flat': False,
        'prefer_free_formats': True,
        'youtube_include_dash_manifest': False,
        'retries': 2,
        'fragment_retries': 2,
        'skip_unavailable_fragments': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Ưu tiên các format âm thanh chất lượng thấp hơn để tránh lỗi
            if 'formats' in info:
                audio_formats = []
                for f in info['formats']:
                    if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                        audio_formats.append(f)
                
                audio_formats.sort(key=lambda x: x.get('abr', 0) or 0)
                
                if audio_formats:
                    chosen_format = audio_formats[0]
                    logging.info(f"Selected audio format: {chosen_format.get('format_id')} - {chosen_format.get('abr', 'unknown')}kbps")
                    return chosen_format.get('url')
            
            return info.get('url')
    except Exception as e:
        logging.error(f"Error getting fresh audio URL for {url}: {e}")
        return None

async def play_next(ctx, voice_client, queues, bot):
    guild_id = str(ctx.guild.id)
    
    # Kiểm tra voice client và kết nối
    if voice_client is None or not voice_client.is_connected():
        logging.warning(f"Voice client disconnected for guild {guild_id}")
        try:
            await ctx.send("🔌 Kết nối voice bị mất. Sử dụng `/play` để phát nhạc tiếp.")
        except:
            pass
        return

    queue = queues.get(guild_id, [])
    if len(queue) == 0:
        if loop_status.get(guild_id, {}).get("mode") == "queue" and loop_status.get(guild_id, {}).get("current_song"):
            # Lặp lại queue: thêm lại bài hát vừa phát xong
            url, _, title, duration = loop_status[guild_id]["current_song"]
            queues[guild_id].append((url, None, title, duration))
            add_to_queue(guild_id, url, "", title, duration)
        else:
            await ctx.send("📭 Queue đã hết. Thêm bài hát mới bằng lệnh `/play`.")
            logging.info(f"No songs left in queue for guild {guild_id}")
            return

    url, _, title, duration = queue[0]

    # Retry mechanism cho việc lấy audio URL
    audio_url = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            audio_url = await get_fresh_audio_url(url)
            if audio_url:
                break
            else:
                logging.warning(f"Attempt {attempt + 1}: Could not get audio URL for {title}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Đợi trước khi thử lại
        except Exception as e:
            logging.error(f"Attempt {attempt + 1}: Error getting audio URL for {title}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)

    if not audio_url:
        await ctx.send(f'❌ Không thể lấy âm thanh cho: **{title}**. Chuyển sang bài tiếp theo.')
        logging.error(f"Could not get audio URL for {title} after {max_retries} attempts")
        queue.pop(0)
        remove_from_queue(guild_id, 0)
        queues[guild_id] = queue
        await play_next(ctx, voice_client, queues, bot)
        return

    try:
        # Cải thiện FFmpeg options
        ffmpeg_options = {
            'before_options': (
                '-reconnect 1 '
                '-reconnect_streamed 1 '
                '-reconnect_delay_max 5 '
                '-analyzeduration 2000000 '
                '-probesize 2000000 '
                '-loglevel error '
                '-nostdin'
            ),
            'options': (
                '-vn '
                '-b:a 96k '
                '-ac 2 '
                '-ar 48000 '
                '-f s16le '
                '-bufsize 1024k '
                '-maxrate 128k'
            )
        }

        def after_playing(error):
            if error:
                logging.error(f"Playback error for {title} in guild {guild_id}: {error}")
                if "return code" not in str(error).lower():
                    asyncio.run_coroutine_threadsafe(
                        ctx.send(f'⚠️ Lỗi phát nhạc: {title}. Chuyển sang bài tiếp theo.'),
                        bot.loop
                    )
            else:
                logging.info(f"Finished playing {title} (duration: {duration}s) in guild {guild_id}")
            
            try:
                if len(queues.get(guild_id, [])) > 0:
                    if loop_status.get(guild_id, {}).get("mode") == "song":
                        # Lặp lại bài hát hiện tại
                        queues[guild_id].insert(0, loop_status[guild_id]["current_song"])
                        add_to_queue(guild_id, url, "", title, duration)
                    else:
                        # Xóa bài hát đã phát nếu không lặp lại
                        queues[guild_id].pop(0)
                        remove_from_queue(guild_id, 0)
                    logging.info(f"Removed finished song from queue for guild {guild_id}")
            except (IndexError, KeyError) as e:
                logging.error(f"Error removing song from queue for guild {guild_id}: {e}")
            
            asyncio.run_coroutine_threadsafe(
                delayed_play_next(ctx, voice_client, queues, bot, 1),
                bot.loop
            )

        source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        if not hasattr(source, 'read') or source is None:
            raise Exception("Invalid audio source created")
        
        logging.info(f"Successfully created audio source for {title}")
        
        # Lưu trạng thái bài hát hiện tại để hỗ trợ loop
        loop_status[guild_id] = {
            "mode": loop_status.get(guild_id, {}).get("mode", "off"),
            "current_song": (url, audio_url, title, duration),
            "start_time": time.time()
        }
        
        voice_client.play(source, after=after_playing)
        
        duration_str = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else "Unknown"
        await ctx.send(f'🎵 Đang phát: **{title}** ({duration_str})')
        logging.info(f"Playing: {title} (duration: {duration}s) for guild {guild_id}")

    except Exception as e:
        await ctx.send(f'❌ Lỗi khi phát **{title}**: {str(e)}')
        logging.error(f"Error playing {title} in guild {guild_id}: {e}")
        try:
            queue.pop(0)
            remove_from_queue(guild_id, 0)
            queues[guild_id] = queue
        except (IndexError, KeyError):
            pass
        await play_next(ctx, voice_client, queues, bot)

async def delayed_play_next(ctx, voice_client, queues, bot, delay=1):
    """Phát bài tiếp theo với delay để tránh lỗi"""
    await asyncio.sleep(delay)
    
    # Kiểm tra lại voice client trước khi phát tiếp
    if voice_client and voice_client.is_connected():
        await play_next(ctx, voice_client, queues, bot)
    else:
        logging.warning(f"Voice client disconnected during delayed_play_next for guild {ctx.guild.id}")

async def get_progress_bar(ctx, queues):
    """Tạo thanh tiến trình cho bài hát đang phát"""
    guild_id = str(ctx.guild.id)
    voice_client = ctx.voice_client
    
    if not voice_client or not voice_client.is_playing():
        return "❌ Không có bài hát nào đang phát."
    
    queue = queues.get(guild_id, [])
    if not queue:
        return "❌ Không có bài hát trong queue."
    
    _, _, title, duration = queue[0]
    if guild_id not in loop_status or not loop_status[guild_id].get("start_time"):
        return f"🎵 Đang phát: **{title}**"
    
    elapsed = time.time() - loop_status[guild_id]["start_time"]
    if duration == 0:
        return f"🎵 Đang phát: **{title}** (Không có thông tin thời lượng)"
    
    progress = min(elapsed / duration, 1.0)
    bar_length = 20
    filled = int(bar_length * progress)
    bar = "█" * filled + "—" * (bar_length - filled)
    elapsed_str = f"{int(elapsed) // 60}:{int(elapsed) % 60:02d}"
    duration_str = f"{duration // 60}:{duration % 60:02d}"
    return f'🎵 Đang phát: **{title}**\n[{bar}] {elapsed_str}/{duration_str}'

async def test_stream_url(url, ctx):
    """Test xem URL stream có hoạt động không"""
    try:
        import subprocess
        import tempfile
        
        cmd = [
            'ffmpeg', 
            '-i', url,
            '-t', '3',
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=15
        )
        
        if result.returncode == 0:
            await ctx.send(f"✅ Stream URL hoạt động tốt")
            return True
        else:
            await ctx.send(f"❌ Stream URL lỗi: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        await ctx.send("⏰ Stream URL timeout")
        return False
    except Exception as e:
        await ctx.send(f"❌ Lỗi test stream: {str(e)}")
        return False