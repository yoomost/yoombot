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
        await ctx.send("❌ Bạn chưa ở trong kênh voice.")
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
            await ctx.send(f"🔄 Đang kết nối đến kênh voice... (Lần thử {attempt + 1}/{retries})")
            voice_client = await channel.connect(timeout=timeout, reconnect=True, self_deaf=True)
            await ctx.send(f"✅ Đã kết nối đến kênh voice: **{channel.name}**")
            logging.info(f"Connected to voice channel {channel.name} on attempt {attempt + 1}")
            return voice_client
        except asyncio.TimeoutError:
            logging.warning(f"Voice connection timeout on attempt {attempt + 1}")
            if attempt < retries - 1:
                await ctx.send("⏰ Kết nối bị timeout, đang thử lại...")
                await asyncio.sleep(2)
            else:
                await ctx.send("❌ Không thể kết nối đến kênh voice sau nhiều lần thử. Vui lòng thử lại sau.")
        except Exception as e:
            logging.error(f"Voice connection error on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                await ctx.send("❌ Lỗi kết nối, đang thử lại...")
                await asyncio.sleep(2)
            else:
                await ctx.send(f"❌ Không thể kết nối đến kênh voice: {str(e)}")
    
    return None

async def get_groq_response(thread_id, message, rag_instance=None, db_type='mental', retries=2):
    logging.info(f"Starting get_groq_response for thread {thread_id}, db_type: {db_type}, message: {message[:50]}...")
    
    try:
        history = get_history(thread_id, limit=20, db_type=db_type)
        history.append({"role": "user", "content": message})
        logging.info(f"Retrieved {len(history)} messages from history for thread {thread_id}")
        
        context = message
        if rag_instance:
            try:
                retrieved_docs = rag_instance.retrieve(message, top_k=3)
                context = "\n".join([f"Document {i+1}: {doc}" for i, doc in enumerate(retrieved_docs)])
                if context:
                    context = f"Retrieved Context:\n{context}\n\nUser Query: {message}"
                logging.info(f"RAG retrieved {len(retrieved_docs)} documents for thread {thread_id}")
            except Exception as e:
                logging.error(f"RAG retrieval error for thread {thread_id}: {str(e)}")
        
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
                
                logging.info(f"Calling Groq API with model {model}, attempt {attempt+1} for thread {thread_id}")
                try:
                    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
                    response.raise_for_status()
                    
                    raw_response = response.text
                    logging.debug(f"Raw Groq API response for thread {thread_id}: {raw_response[:500]}...")
                    
                    if not raw_response.strip():
                        logging.error(f"Empty response from Groq API for thread {thread_id}")
                        if attempt < retries - 1:
                            await asyncio.sleep(2)
                            continue
                        return f"Error: Empty response from Groq API (thread {thread_id})"
                    
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
                                logging.error(f"Chunk decode error for thread {thread_id}: {str(e)}, chunk: {chunk}")
                    
                    if api_response:
                        add_message(thread_id, None, "assistant", api_response, db_type)
                        logging.info(f"Generated response for thread {thread_id}: {api_response[:100]}...")
                        return api_response
                    else:
                        logging.error(f"No content in streaming response for thread {thread_id}")
                        if attempt < retries - 1:
                            await asyncio.sleep(2)
                            continue
                        return f"Error: No content received from Groq API (thread {thread_id})"
                
                except requests.exceptions.RequestException as e:
                    logging.error(f"Groq API error for thread {thread_id} (model: {model}, attempt: {attempt+1}): {str(e)}")
                    if "rate_limit" in str(e).lower() or (isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429):
                        if attempt < retries - 1:
                            await asyncio.sleep(5)
                            continue
                    if attempt < retries - 1 and model == models[0]:
                        logging.info(f"Retrying with fallback model: {models[1]} for thread {thread_id}")
                        continue
                    return f"Error calling Groq API for thread {thread_id}: {str(e)}"
        
        logging.error(f"Failed to get Groq API response for thread {thread_id} after {retries} attempts")
        return f"Error: Failed to get response from Groq API after retries (thread {thread_id})"
    
    except Exception as e:
        logging.error(f"Unexpected error in get_groq_response for thread {thread_id}: {str(e)}")
        return f"Error: Unexpected issue processing request for thread {thread_id}: {str(e)}"