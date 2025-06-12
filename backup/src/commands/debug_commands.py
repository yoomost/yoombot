import discord
from discord.ext import commands
import yt_dlp
import logging
import subprocess
import os
import shutil
import asyncio
from src.music.player import get_fresh_audio_url
from src.music.utils import test_stream_url
from src.utils.helpers import safe_voice_connect

def setup_debug_commands(bot, queues):
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
        """
        await ctx.send(debug_info)

    @bot.command(name='ffmpeg_test', help='Test FFmpeg')
    async def ffmpeg_test(ctx):
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            await ctx.send(f"FFmpeg version: {result.stdout[:500]}")
        except Exception as e:
            await ctx.send(f"FFmpeg error: {e}")

    @bot.command(name='test_stream', help='Test stream URL cho debug')
    async def test_stream(ctx, *, query: str):
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