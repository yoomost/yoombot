import discord
import requests
import json
import logging
import asyncio
from config import GROQ_API_KEY
from database import get_history, add_message

async def safe_voice_connect(ctx, timeout=10, retries=3):
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

async def get_groq_response(channel_id, message):
    # Lấy lịch sử trò chuyện từ CSDL, tăng giới hạn lên 20 để có ngữ cảnh đầy đủ hơn
    history = get_history(channel_id, limit=20)
    
    # Thêm tin nhắn người dùng hiện tại
    history.append({"role": "user", "content": message})
    
    # Tạo lịch sử đầy đủ với tin nhắn hệ thống
    full_history = [{"role": "system", "content": "You are a helpful assistant. Maintain context from previous messages to provide coherent responses."}] + history
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": full_history,
        "max_tokens": 8192,
        "stream": False,
        "temperature": 0.7  # Thêm temperature để tăng tính tự nhiên
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        api_response = response.json()["choices"][0]["message"]["content"]
        
        # Lưu câu trả lời vào CSDL
        add_message(channel_id, None, "assistant", api_response)
        return api_response
    except requests.exceptions.RequestException as e:
        logging.error(f"Groq API error: {str(e)}")
        return f"Error calling Groq API: {str(e)}"