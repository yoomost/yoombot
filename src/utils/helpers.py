import discord
import requests
import json
import logging
import asyncio
from config import GROQ_API_KEY
from database import get_history, add_message
from src.utils.rag import RAG  # Import the new RAG module

# Initialize RAG system
rag = RAG(embed_model="all-MiniLM-L6-v2", index_path="./data/rag_index", doc_dir="./data/documents")

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
    # Lấy lịch sử trò chuyện từ CSDL
    history = get_history(channel_id, limit=20)
    
    # Thêm tin nhắn người dùng hiện tại
    history.append({"role": "user", "content": message})
    
    # Retrieve relevant documents using RAG
    try:
        retrieved_docs = rag.retrieve(message, top_k=3)
        context = "\n".join([f"Document {i+1}: {doc}" for i, doc in enumerate(retrieved_docs)])
        if context:
            context = f"Retrieved Context:\n{context}\n\nUser Query: {message}"
        else:
            context = message
    except Exception as e:
        logging.error(f"RAG retrieval error: {str(e)}")
        context = message
    
    # Tạo lịch sử đầy đủ với tin nhắn hệ thống và ngữ cảnh RAG
    full_history = [
        {"role": "system", "content": "You are a helpful assistant. Use the provided context and maintain coherence with previous messages."},
        {"role": "user", "content": context}
    ] + history[-5:]  # Limit history to last 5 messages to avoid token overflow
    
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
        "temperature": 0.7
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