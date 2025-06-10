import discord
import yt_dlp
import logging
import asyncio
from database import add_to_queue, get_queue, remove_from_queue

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
    
    # Nếu không phải URL, thêm prefix tìm kiếm YouTube
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

async def get_fresh_audio_url(url):
    """Lấy URL âm thanh mới từ video URL để tránh hết hạn"""
    ydl_opts = {
        'format': 'bestaudio[abr<=128]/bestaudio/best[height<=480]',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 15,
        'force_json': True,
        'extract_flat': False,
        'prefer_free_formats': True,
        'youtube_include_dash_manifest': False,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Ưu tiên các format âm thanh chất lượng thấp hơn để tránh lỗi
            if 'formats' in info:
                audio_formats = []
                for f in info['formats']:
                    if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                        # Chỉ lấy format âm thanh thuần túy
                        audio_formats.append(f)
                
                # Sắp xếp theo abr (audio bitrate) từ thấp đến cao
                audio_formats.sort(key=lambda x: x.get('abr', 0) or 0)
                
                if audio_formats:
                    # Chọn format có bitrate thấp nhất để ổn định
                    chosen_format = audio_formats[0]
                    logging.info(f"Selected audio format: {chosen_format.get('format_id')} - {chosen_format.get('abr', 'unknown')}kbps")
                    return chosen_format.get('url')
            
            # Fallback to default URL
            return info.get('url')
            
    except Exception as e:
        logging.error(f"Error getting fresh audio URL for {url}: {e}")
        return None

async def play_next(ctx, voice_client, queues, bot):
    guild_id = str(ctx.guild.id)
    
    # Kiểm tra kết nối voice với xử lý lỗi tốt hơn
    if voice_client is None or not voice_client.is_connected():
        logging.warning(f"Voice client disconnected for guild {guild_id}")
        try:
            await ctx.send("🔌 Kết nối voice bị mất. Sử dụng `!play` để phát nhạc tiếp.")
        except:
            pass
        return

    # Lấy queue của guild
    queue = queues.get(guild_id, [])
    if len(queue) == 0:
        await ctx.send("📭 Queue đã hết. Thêm bài hát mới bằng lệnh `!play`.")
        logging.info(f"No songs left in queue for guild {guild_id}")
        return

    # Lấy bài hát tiếp theo từ queue
    url, _, title, duration = queue[0]

    # Lấy URL âm thanh mới để tránh hết hạn
    audio_url = await get_fresh_audio_url(url)
    if not audio_url:
        await ctx.send(f'❌ Không thể lấy âm thanh cho: **{title}**. Chuyển sang bài tiếp theo.')
        logging.error(f"Could not get audio URL for {title}")
        # Xóa bài hát lỗi khỏi queue
        queue.pop(0)
        remove_from_queue(guild_id, 0)
        queues[guild_id] = queue
        # Thử phát bài tiếp theo
        await play_next(ctx, voice_client, queues, bot)
        return

    try:
        # Cấu hình FFmpeg đơn giản hóa để tránh lỗi
        ffmpeg_options = {
            'before_options': (
                '-reconnect 1 '
                '-reconnect_streamed 1 '
                '-reconnect_delay_max 5 '
                '-analyzeduration 0 '
                '-loglevel error '
                '-nostdin'
            ),
            'options': (
                '-vn '
                '-b:a 96k '
                '-ac 2 '
                '-ar 48000 '
                '-f s16le '
                '-bufsize 512k'
            )
        }

        # Callback sau khi phát xong với xử lý lỗi tốt hơn
        def after_playing(error):
            if error:
                logging.error(f"Playback error for {title} in guild {guild_id}: {error}")
                # Không gửi thông báo lỗi cho user nếu chỉ là lỗi FFmpeg nhỏ
                if "return code" not in str(error).lower():
                    asyncio.run_coroutine_threadsafe(
                        ctx.send(f'⚠️ Lỗi phát nhạc: {title}. Chuyển sang bài tiếp theo.'),
                        bot.loop
                    )
            else:
                logging.info(f"Finished playing {title} (duration: {duration}s) in guild {guild_id}")
            
            # Xóa bài hát đã phát xong khỏi queue
            try:
                if len(queues.get(guild_id, [])) > 0:
                    queues[guild_id].pop(0)
                    remove_from_queue(guild_id, 0)
                    logging.info(f"Removed finished song from queue for guild {guild_id}")
            except (IndexError, KeyError) as e:
                logging.error(f"Error removing song from queue for guild {guild_id}: {e}")
            
            # Phát bài tiếp theo với delay nhỏ để tránh lỗi
            asyncio.run_coroutine_threadsafe(
                delayed_play_next(ctx, voice_client, queues, bot, 1),
                bot.loop
            )

        # Tạo audio source với xử lý lỗi cải thiện
        try:
            # Tạo source đơn giản trước
            source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
            
            # Kiểm tra xem source có hoạt động không
            if not hasattr(source, 'read') or source is None:
                raise Exception("Invalid audio source created")
                
            logging.info(f"Successfully created audio source for {title}")
            
        except Exception as source_error:
            logging.error(f"Error creating audio source for {title}: {source_error}")
            await ctx.send(f'❌ Không thể tạo nguồn âm thanh cho: **{title}**. Chuyển sang bài tiếp theo.')
            # Xóa bài hát lỗi và thử phát bài tiếp theo
            queue.pop(0)
            remove_from_queue(guild_id, 0)
            queues[guild_id] = queue
            await play_next(ctx, voice_client, queues, bot)
            return

        # Kiểm tra voice client trước khi phát
        if not voice_client.is_connected():
            await ctx.send("🔌 Kết nối voice bị mất trước khi phát nhạc.")
            return

        voice_client.play(source, after=after_playing)
        
        duration_str = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else "Unknown"
        await ctx.send(f'🎵 Đang phát: **{title}** ({duration_str})')
        logging.info(f"Playing: {title} (duration: {duration}s) for guild {guild_id}")

    except Exception as e:
        await ctx.send(f'❌ Lỗi khi phát **{title}**: {str(e)}')
        logging.error(f"Error playing {title} in guild {guild_id}: {e}")
        # Xóa bài hát lỗi và thử phát bài tiếp theo
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
    await play_next(ctx, voice_client, queues, bot)

async def test_stream_url(url, ctx):
    """Test xem URL stream có hoạt động không"""
    try:
        import subprocess
        import tempfile
        
        # Test với FFmpeg timeout 10s
        cmd = [
            'ffmpeg', 
            '-i', url,
            '-t', '3',  # Test 3 giây đầu
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