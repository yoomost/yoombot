import discord
import aiohttp
from aiohttp import FormData
import json
import logging
import asyncio
from config import GROQ_API_KEY, XAI_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY
from database import get_history, add_message, add_gpt_batch_job, update_gpt_batch_job, get_gpt_batch_job, get_pending_gpt_batch_jobs
from src.utils.rag import RAG
import uuid
from datetime import datetime

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
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=60, sock_read=600)
        async with aiohttp.ClientSession(timeout=timeout) as session:
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
                        async with session.post(url, headers=headers, json=data) as response:
                            response.raise_for_status()
                            api_response = ""
                            async for line in response.content:
                                line = line.decode('utf-8').strip()
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
                    except aiohttp.ClientResponseError as e:
                        logging.error(f"Groq API error for thread {thread_id} (model: {model}, attempt: {attempt+1}): {str(e)}, status: {e.status}, message: {e.message}")
                        if e.status == 429:
                            if attempt < retries - 1:
                                await asyncio.sleep(5 * (2 ** attempt))
                                continue
                        if attempt < retries - 1 and model == models[0]:
                            logging.info(f"Retrying with fallback model: {models[1]} for thread {thread_id}")
                            continue
                        return f"Error calling Groq API for thread {thread_id}: {str(e)}"
                    except aiohttp.ClientConnectionError as e:
                        logging.error(f"Connection error in Groq API call for thread {thread_id}: {str(e)}")
                        if attempt < retries - 1:
                            await asyncio.sleep(5 * (2 ** attempt))
                            continue
                        return f"Error: Connection issue in Groq API call for thread {thread_id}: {str(e)}"
                    except asyncio.TimeoutError as e:
                        logging.error(f"Timeout error in Groq API call for thread {thread_id}: {str(e)}")
                        if attempt < retries - 1:
                            await asyncio.sleep(5 * (2 ** attempt))
                            continue
                        return f"Error: Timeout in Groq API call for thread {thread_id}: {str(e)}"
                    except Exception as e:
                        logging.error(f"Unexpected error in Groq API call for thread {thread_id}: {str(e)}, type: {type(e).__name__}")
                        return f"Error: Unexpected issue in Grok API call for thread {thread_id}: {str(e)}"
        logging.error(f"Failed to get Groq API response for thread {thread_id} after {retries} attempts")
        return f"Error: Failed to get response from Groq API after retries (thread {thread_id})"
    except Exception as e:
        logging.error(f"Unexpected error in get_groq_response for thread {thread_id}: {str(e)}, type: {type(e).__name__}")
        return f"Error: Unexpected issue processing request for thread {thread_id}: {str(e)}"

async def get_xai_response(thread_id, message, user_id, mode=None, retries=2):
    logging.info(f"Starting get_xai_response for thread {thread_id}, user: {user_id}, mode: {mode}, message: {message[:50]}...")
    try:
        history = get_history(thread_id, limit=20, db_type='grok4', user_id=user_id)
        logging.info(f"Retrieved {len(history)} messages from history for thread {thread_id}, user {user_id}")
        full_history = [
            {"role": "system", "content": "You are Grok 4, created by xAI. Provide accurate, detailed, and helpful responses. For DeepSearch, include real-time web and X data with citations. For DeeperSearch, focus on deep reasoning with minimal sources. For Think Mode, provide step-by-step reasoning. Maintain coherence with previous messages."}
        ] + history[-5:] + [{"role": "user", "content": message}]
        url = "https://api.x.ai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {XAI_API_KEY}"
        }
        data = {
            "model": "grok-4",
            "messages": full_history,
            "max_tokens": 8192,
            "stream": True,
            "temperature": 0.7
        }
        if mode in ['deepsearch', 'deepersearch', 'think']:
            data["mode"] = mode
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=60, sock_read=600)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(retries):
                logging.info(f"Calling xAI API with model grok-4, attempt {attempt+1}, mode: {mode} for thread {thread_id}")
                try:
                    async with session.post(url, headers=headers, json=data) as response:
                        response.raise_for_status()
                        api_response = ""
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
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
                                add_message(thread_id, None, "assistant", api_response, db_type='grok4', mode=mode, user_id=user_id)
                                logging.info(f"Generated response for thread {thread_id}: {api_response[:100]}...")
                                return api_response
                            else:
                                logging.error(f"No content in streaming response for thread {thread_id}")
                                if attempt < retries - 1:
                                    await asyncio.sleep(2)
                                    continue
                                return f"Error: No content received from xAI API (thread {thread_id})"
                except aiohttp.ClientResponseError as e:
                    logging.error(f"xAI API error for thread {thread_id} (attempt: {attempt+1}): {str(e)}, status: {e.status}, message: {e.message}")
                    if e.status == 429:
                        if attempt < retries - 1:
                            await asyncio.sleep(5 * (2 ** attempt))
                            continue
                    return f"Error calling xAI API for thread {thread_id}: {str(e)}"
                except aiohttp.ClientConnectionError as e:
                    logging.error(f"Connection error in xAI API call for thread {thread_id}: {str(e)}")
                    if attempt < retries - 1:
                        await asyncio.sleep(5 * (2 ** attempt))
                        continue
                    return f"Error: Connection issue in xAI API call for thread {thread_id}: {str(e)}"
                except asyncio.TimeoutError as e:
                    logging.error(f"Timeout error in xAI API call for thread {thread_id}: {str(e)}")
                    if attempt < retries - 1:
                        await asyncio.sleep(5 * (2 ** attempt))
                        continue
                    return f"Error: Timeout in xAI API call for thread {thread_id}: {str(e)}"
                except Exception as e:
                    logging.error(f"Unexpected error in xAI API call for thread {thread_id}: {str(e)}, type: {type(e).__name__}")
                    return f"Error: Unexpected issue in xAI API call for thread {thread_id}: {str(e)}"
        logging.error(f"Failed to get xAI API response for thread {thread_id} after {retries} attempts")
        return f"Error: Failed to get response from xAI API after retries (thread {thread_id})"
    except Exception as e:
        logging.error(f"Unexpected error in get_xai_response for thread {thread_id}: {str(e)}, type: {type(e).__name__}")
        return f"Error: Unexpected issue processing request for thread {thread_id}: {str(e)}"

async def get_gemini_response(thread_id, message, db_type='gemini', retries=2):
    logging.info(f"Starting get_gemini_response for thread {thread_id}, db_type: {db_type}, message: {message[:50]}...")
    try:
        history = get_history(thread_id, limit=20, db_type=db_type)
        logging.info(f"Retrieved {len(history)} messages from history for thread {thread_id}")
        gemini_history = []
        for msg in history[-5:]:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [{"text": msg["content"]}]})
        gemini_history.append({"role": "user", "parts": [{"text": message}]})
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:streamGenerateContent?key={GEMINI_API_KEY}"
        headers = {
            "Content-Type": "application/json",
        }
        data = {
            "contents": gemini_history,
            "generationConfig": {
                "maxOutputTokens": 8192,
                "temperature": 0.7,
            }
        }
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=60, sock_read=600)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(retries):
                logging.info(f"Calling Gemini API, attempt {attempt+1} for thread {thread_id}")
                try:
                    async with session.post(url, headers=headers, json=data) as response:
                        response.raise_for_status()
                        api_response = ""
                        buffer = ""
                        async for line_bytes in response.content:
                            line = line_bytes.decode('utf-8').strip()
                            if not line:
                                continue
                            try:
                                chunk_data_list = json.loads(line)
                                for chunk_data in chunk_data_list:
                                    if "candidates" in chunk_data and chunk_data["candidates"]:
                                        candidate = chunk_data["candidates"][0]
                                        if "content" in candidate and "parts" in candidate["content"]:
                                            for part in candidate["content"]["parts"]:
                                                if "text" in part:
                                                    api_response += part["text"]
                                                else:
                                                    logging.warning(f"Gemini chunk part has no 'text' field for thread {thread_id}: {part}")
                                        else:
                                            logging.warning(f"Gemini chunk candidate missing 'content' or 'parts' for thread {thread_id}: {candidate}")
                                    else:
                                        logging.warning(f"Gemini chunk missing 'candidates' or candidates empty for thread {thread_id}: {chunk_data}")
                                buffer = ""
                                logging.debug(f"Successfully parsed standalone line for thread {thread_id}.")
                            except json.JSONDecodeError:
                                buffer += line
                                try:
                                    chunk_data_list = json.loads(buffer)
                                    for chunk_data in chunk_data_list:
                                        if "candidates" in chunk_data and chunk_data["candidates"]:
                                            candidate = chunk_data["candidates"][0]
                                            if "content" in candidate and "parts" in candidate["content"]:
                                                for part in candidate["content"]["parts"]:
                                                    if "text" in part:
                                                        api_response += part["text"]
                                                    else:
                                                        logging.warning(f"Gemini chunk part has no 'text' field for thread {thread_id}: {part}")
                                            else:
                                                logging.warning(f"Gemini chunk candidate missing 'content' or 'parts' for thread {thread_id}: {candidate}")
                                        else:
                                            logging.warning(f"Gemini chunk missing 'candidates' or candidates empty for thread {thread_id}: {chunk_data}")
                                    buffer = ""
                                    logging.debug(f"Successfully parsed accumulated buffer for thread {thread_id}.")
                                except json.JSONDecodeError as e:
                                    if "Extra data" not in str(e) and "Expecting value" not in str(e) and "Expecting property name" not in str(e) and "Expecting ',' delimiter" not in str(e):
                                        logging.warning(f"Buffer is not complete JSON yet or malformed for thread {thread_id}: '{buffer[:50]}...'. Error: {e}")
                                    logging.debug(f"Still accumulating buffer for thread {thread_id}: '{buffer[:50]}...'")
                                    pass
                                except Exception as e:
                                    logging.error(f"Error processing accumulated Gemini chunk for thread {thread_id}: {str(e)}, raw buffer: '{buffer[:100]}...'")
                                    buffer = ""
                        if buffer:
                            try:
                                chunk_data_list = json.loads(buffer)
                                for chunk_data in chunk_data_list:
                                    if "candidates" in chunk_data and chunk_data["candidates"]:
                                        candidate = chunk_data["candidates"][0]
                                        if "content" in candidate and "parts" in candidate["content"]:
                                            for part in candidate["content"]["parts"]:
                                                if "text" in part:
                                                    api_response += part["text"]
                            except json.JSONDecodeError as e:
                                logging.warning(f"Remaining buffer is not complete JSON at end of stream for thread {thread_id}: '{buffer[:50]}...'. Error: {e}")
                            except Exception as e:
                                logging.error(f"Error processing remaining Gemini buffer for thread {thread_id}: {str(e)}, raw buffer: '{buffer[:100]}...'")
                        if api_response:
                            add_message(thread_id, None, "assistant", api_response, db_type)
                            logging.info(f"Generated response for thread {thread_id}: {api_response[:100]}...")
                            return api_response
                        else:
                            final_raw_response_text = ""
                            try:
                                if not response.content.at_eof():
                                    final_raw_response_text = await response.text()
                            except Exception as e:
                                logging.warning(f"Could not get full response text for thread {thread_id}: {e}")
                            logging.error(f"No content in streaming response from Gemini for thread {thread_id}. Final raw response (if any): {final_raw_response_text}")
                            if attempt < retries - 1:
                                await asyncio.sleep(2)
                                continue
                            return f"Error: No content received from Gemini API (thread {thread_id})"
                except aiohttp.ClientResponseError as e:
                    logging.error(f"Gemini API error for thread {thread_id} (attempt: {attempt+1}): {str(e)}, status: {e.status}, message: {e.message}")
                    if e.status == 429:
                        if attempt < retries - 1:
                            await asyncio.sleep(5 * (2 ** attempt))
                            continue
                    return f"Error calling Gemini API for thread {thread_id}: {str(e)}"
                except aiohttp.ClientConnectionError as e:
                    logging.error(f"Connection error in Gemini API call for thread {thread_id}: {str(e)}")
                    if attempt < retries - 1:
                        await asyncio.sleep(5 * (2 ** attempt))
                        continue
                    return f"Error: Connection issue in Gemini API call for thread {thread_id}: {str(e)}"
                except asyncio.TimeoutError as e:
                    logging.error(f"Timeout error in Gemini API call for thread {thread_id}: {str(e)}")
                    if attempt < retries - 1:
                        await asyncio.sleep(5 * (2 ** attempt))
                        continue
                    return f"Error: Timeout in Gemini API call for thread {thread_id}: {str(e)}"
                except Exception as e:
                    logging.error(f"Unexpected error in Gemini API call for thread {thread_id}: {str(e)}, type: {type(e).__name__}")
                    return f"Error: Unexpected issue in Gemini API call for thread {thread_id}: {str(e)}"
        logging.error(f"Failed to get Gemini API response for thread {thread_id} after {retries} attempts")
        return f"Error: Failed to get response from Gemini API after retries (thread {thread_id})"
    except Exception as e:
        logging.error(f"Unexpected error in get_gemini_response for thread {thread_id}: {str(e)}, type: {type(e).__name__}")
        return f"Error: Unexpected issue processing request for thread {thread_id}: {str(e)}"

async def get_gpt_response(thread_id, message, user_id, db_type='gpt', retries=2, file_content=None):
    logging.info(f"Starting get_gpt_response for thread {thread_id}, user: {user_id}, db_type: {db_type}, message: {message[:50]}...")
    try:
        history = get_history(thread_id, limit=20, db_type=db_type, user_id=user_id)
        logging.info(f"Retrieved {len(history)} messages from history for thread {thread_id}, user {user_id}")
        full_history = [
            {"role": "system", "content": "You are a helpful assistant powered by GPT-4.1, created by OpenAI. Provide accurate, detailed, and coherent responses based on the provided context and maintain conversation history."}
        ] + history[-5:] + [{"role": "user", "content": message + (f"\n\nFile content: {file_content}" if file_content else "")}]
        
        # Generate a unique batch ID
        batch_id = str(uuid.uuid4())
        request_data = json.dumps({
            "custom_id": f"request-{batch_id}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "gpt-4o",
                "messages": full_history,
                "max_tokens": 8192,
                "temperature": 0.7
            }
        }, ensure_ascii=False) + "\n"  # Ensure UTF-8 encoding and JSONL format
        
        # Store the batch job in the database
        add_gpt_batch_job(batch_id, thread_id, user_id, request_data)
        
        # Prepare batch job for OpenAI Batch API
        batch_request = {
            "input_file_id": f"file-{batch_id}",
            "endpoint": "/v1/chat/completions",
            "completion_window": "24h",
            "metadata": {"thread_id": thread_id, "user_id": user_id}
        }
        
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=60, sock_read=600)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Step 1: Upload request data as a file
            try:
                upload_url = "https://api.openai.com/v1/files"
                form = FormData()
                form.add_field("file", request_data.encode('utf-8'), filename=f"batch-{batch_id}.jsonl")  # Use text/plain implicitly
                form.add_field("purpose", "batch")
                async with session.post(upload_url, headers=headers, data=form) as response:
                    response.raise_for_status()
                    upload_data = await response.json()
                    input_file_id = upload_data.get("id")
                    logging.info(f"Uploaded batch request file {input_file_id} for thread {thread_id}")
            except aiohttp.ClientResponseError as e:
                logging.error(f"Error uploading batch request file for thread {thread_id}: {str(e)}, status: {e.status}, message: {e.message}, request_data: {request_data[:100]}...")
                update_gpt_batch_job(batch_id, "failed")
                return f"Error: Failed to upload batch request for thread {thread_id}: {str(e)}"
            except Exception as e:
                logging.error(f"Error uploading batch request file for thread {thread_id}: {str(e)}")
                update_gpt_batch_job(batch_id, "failed")
                return f"Error: Failed to upload batch request for thread {thread_id}: {str(e)}"
            
            # Step 2: Submit batch job
            try:
                batch_url = "https://api.openai.com/v1/batches"
                batch_request["input_file_id"] = input_file_id
                async with session.post(batch_url, headers=headers, json=batch_request) as response:
                    response.raise_for_status()
                    batch_data = await response.json()
                    batch_id = batch_data.get("id")
                    update_gpt_batch_job(batch_id, "submitted")
                    logging.info(f"Submitted batch job {batch_id} for thread {thread_id}")
                    return f"Batch job submitted with ID: {batch_id}. Response will be sent to this thread when ready, or use `!gpt retrieve {batch_id}` in any thread."
            except aiohttp.ClientResponseError as e:
                logging.error(f"Error submitting batch job for thread {thread_id}: {str(e)}, status: {e.status}, message: {e.message}")
                update_gpt_batch_job(batch_id, "failed")
                return f"Error: Failed to submit batch job for thread {thread_id}: {str(e)}"
            except Exception as e:
                logging.error(f"Error submitting batch job for thread {thread_id}: {str(e)}")
                update_gpt_batch_job(batch_id, "failed")
                return f"Error: Failed to submit batch job for thread {thread_id}: {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected error in get_gpt_response for thread {thread_id}: {str(e)}, type: {type(e).__name__}")
        return f"Error: Unexpected issue processing request for thread {thread_id}: {str(e)}"
    
async def check_gpt_batch_jobs(bot, interval=300):
    """Periodically check for completed GPT-4.1 batch jobs."""
    while True:
        try:
            pending_jobs = get_pending_gpt_batch_jobs()
            logging.info(f"Checking {len(pending_jobs)} pending GPT-4.1 batch jobs")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            timeout = aiohttp.ClientTimeout(total=None, sock_connect=60, sock_read=600)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for job in pending_jobs:
                    batch_id = job['batch_id']
                    thread_id = job['thread_id']
                    user_id = job['user_id']
                    try:
                        # Check batch job status
                        url = f"https://api.openai.com/v1/batches/{batch_id}"
                        async with session.get(url, headers=headers) as response:
                            response.raise_for_status()
                            batch_data = await response.json()
                            status = batch_data.get("status")
                            if status in ["completed", "failed", "expired", "cancelled"]:
                                update_gpt_batch_job(batch_id, status, batch_data.get("response_data"), datetime.now().isoformat())
                                if status == "completed":
                                    # Retrieve response from output file
                                    output_file_id = batch_data.get("output_file_id")
                                    if output_file_id:
                                        file_url = f"https://api.openai.com/v1/files/{output_file_id}/content"
                                        async with session.get(file_url, headers=headers) as file_response:
                                            file_response.raise_for_status()
                                            response_text = await file_response.text()
                                            try:
                                                response_data = json.loads(response_text)
                                                api_response = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                                                if api_response:
                                                    add_message(thread_id, None, "assistant", api_response, db_type='gpt', user_id=user_id, batch_id=batch_id)
                                                    thread = bot.get_channel(int(thread_id))
                                                    if thread:
                                                        chunks = [api_response[i:i+1900] for i in range(0, len(api_response), 1900)]
                                                        for i, chunk in enumerate(chunks):
                                                            prefix = f"**Batch ID: {batch_id}**\n" if i == 0 else ""
                                                            await thread.send(f"{prefix}{chunk}")
                                                        logging.info(f"Sent GPT-4.1 response for batch {batch_id} to thread {thread_id}")
                                                    else:
                                                        logging.error(f"Thread {thread_id} not found for batch {batch_id}")
                                                else:
                                                    logging.error(f"No content in GPT-4.1 response for batch {batch_id}")
                                                    thread = bot.get_channel(int(thread_id))
                                                    if thread:
                                                        await thread.send(f"Error: No content received for batch {batch_id}")
                                            except json.JSONDecodeError as e:
                                                logging.error(f"Error parsing GPT-4.1 batch response for batch {batch_id}: {str(e)}")
                                                thread = bot.get_channel(int(thread_id))
                                                if thread:
                                                    await thread.send(f"Error: Failed to parse batch response for {batch_id}")
                                        update_gpt_batch_job(batch_id, "processed", response_text, datetime.now().isoformat())
                                    else:
                                        logging.error(f"No output file ID for completed batch {batch_id}")
                                        thread = bot.get_channel(int(thread_id))
                                        if thread:
                                            await thread.send(f"Error: No output file for batch {batch_id}")
                                        update_gpt_batch_job(batch_id, "failed")
                                elif status in ["failed", "expired", "cancelled"]:
                                    thread = bot.get_channel(int(thread_id))
                                    if thread:
                                        await thread.send(f"Batch job {batch_id} {status}. Please try again.")
                                    logging.info(f"Batch job {batch_id} marked as {status}")
                    except Exception as e:
                        logging.error(f"Error checking GPT-4.1 batch job {batch_id}: {str(e)}")
            await asyncio.sleep(interval)
        except Exception as e:
            logging.error(f"Error in check_gpt_batch_jobs: {str(e)}")
            await asyncio.sleep(interval)