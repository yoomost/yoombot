import discord
import logging
import time
import subprocess

async def get_progress_bar(ctx, queues, loop_status):
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
    try:
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