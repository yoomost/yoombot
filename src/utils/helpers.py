import discord
import requests
import json
import logging
import asyncio
import time
from config import GROQ_API_KEY
from database import get_history, add_message
from src.utils.rag import RAG

# Initialize RAG for mental health channel only
mental_rag = RAG(embed_model="all-MiniLM-L6-v2", index_path="./data/rag_index/mental", doc_dir="./data/documents/mental_counseling")

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

async def get_groq_response(channel_id, message, rag_instance=None, db_type='mental', retries=2):
    history = get_history(channel_id, limit=20, db_type=db_type)
    history.append({"role": "user", "content": message})
    
    context = message
    if rag_instance:
        try:
            retrieved_docs = rag_instance.retrieve(message, top_k=3)
            context = "\n".join([f"Document {i+1}: {doc}" for i, doc in enumerate(retrieved_docs)])
            if context:
                context = f"Retrieved Context:\n{context}\n\nUser Query: {message}"
        except Exception as e:
            logging.error(f"RAG retrieval error: {str(e)}")
    
    full_history = [
        {"role": "system", "content": "You are a helpful assistant. For the mental health channel, provide empathetic and professional counseling advice. For the general channel, offer accurate and informative responses. Use the provided context and maintain coherence with previous messages."},
        {"role": "user", "content": context}
    ] + history[-5:]
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    models = ["llama3-70b-8192", "llama-3.1-8b-instant"]
    
    for attempt in range(retries):
        for model in models:
            data = {
                "model": model,
                "messages": full_history,
                "max_tokens": 8192,
                "stream": True,
                "temperature": 0.7
            }
            
            try:
                response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
                response.raise_for_status()
                
                raw_response = response.text
                logging.info(f"Raw Groq API response: {raw_response[:500]}...")
                
                if not raw_response.strip():
                    logging.error("Empty response from Groq API")
                    if attempt < retries - 1:
                        await asyncio.sleep(2)
                        continue
                    return "Error: Empty response from Groq API"
                
                api_response = ""
                for line in raw_response.splitlines():
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(chunk)
                            if "choices" in chunk_data and chunk_data["choices"]:
                                delta = chunk_data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    api_response += content
                        except json.JSONDecodeError as e:
                            logging.error(f"Chunk decode error: {str(e)}")
                
                if api_response:
                    add_message(channel_id, None, "assistant", api_response, db_type)
                    return api_response
                else:
                    logging.error("No content in streaming response")
                    if attempt < retries - 1:
                        await asyncio.sleep(2)
                        continue
                    return "Error: No content received from Groq API"
                
            except requests.exceptions.RequestException as e:
                logging.error(f"Groq API error (model: {model}, attempt: {attempt+1}): {str(e)}")
                if "rate_limit" in str(e).lower() or isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429:
                    if attempt < retries - 1:
                        await asyncio.sleep(5)
                        continue
                if attempt < retries - 1 and model == models[0]:
                    logging.info(f"Retrying with fallback model: {models[1]}")
                    continue
                return f"Error calling Groq API: {str(e)}"
    
    return "Error: Failed to get response from Groq API after retries"