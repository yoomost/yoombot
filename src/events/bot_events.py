import discord
from discord.ext import commands
import logging
import asyncio
import json
from datetime import datetime
from config import MENTAL_CHANNEL_ID, GENERAL_CHANNEL_ID, WELCOME_CHANNEL_ID, NEWS_CHANNEL_ID, GROK4_CHANNEL_ID, GPT_CHANNEL_ID, GEMINI_CHANNEL_ID
from database import get_history, add_message, is_message_exists, get_gpt_batch_job, get_queue, update_gpt_batch_job
from src.utils.helpers import get_groq_response, get_xai_response, get_gpt_response, get_gemini_response, mental_rag, check_gpt_batch_jobs
from src.utils.news import news_task

def setup_events(bot, queues, loop_status):

    async def cleanup_handled_messages(bot, interval=600):
        while True:
            await asyncio.sleep(interval)
            if hasattr(bot, "_handled_messages"):
                bot._handled_messages.clear()
                logging.debug("Cleared handled message cache")

    @bot.event
    async def on_ready():
        logging.info(f"Bot {bot.user} connected to Discord")
        for guild in bot.guilds:
            guild_id = str(guild.id)
            queues[guild_id] = get_queue(guild_id)
            logging.info(f"Loaded queue for guild {guild_id}")
        await bot.tree.sync()
        logging.info("Bot started, queues loaded, and slash commands synced")
        bot.loop.create_task(news_task(bot))
        bot.loop.create_task(cleanup_handled_messages(bot))
        bot.loop.create_task(check_gpt_batch_jobs(bot))  # Start checking GPT-4.1 batch jobs
        logging.info("Started background tasks")

    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            return

        if not hasattr(bot, "_handled_messages"):
            bot._handled_messages = set()
        if message.id in bot._handled_messages:
            return
        bot._handled_messages.add(message.id)

        if message.webhook_id is not None:
            return

        logging.info(f"Received message from {message.author.name} (ID: {message.author.id}) in channel/thread {message.channel.id}")

        parent_channel_id = message.channel.parent_id if isinstance(message.channel, discord.Thread) else message.channel.id
        if parent_channel_id in [MENTAL_CHANNEL_ID, GENERAL_CHANNEL_ID, GROK4_CHANNEL_ID, GPT_CHANNEL_ID, GEMINI_CHANNEL_ID]:
            db_type = None
            if parent_channel_id == MENTAL_CHANNEL_ID:
                db_type = 'mental'
            elif parent_channel_id == GENERAL_CHANNEL_ID:
                db_type = 'general'
            elif parent_channel_id == GROK4_CHANNEL_ID:
                db_type = 'grok4'
            elif parent_channel_id == GPT_CHANNEL_ID:
                db_type = 'gpt'
            elif parent_channel_id == GEMINI_CHANNEL_ID:
                db_type = 'gemini'

            thread_name = f"{message.author.name}-private-{db_type}-chat"
            logging.info(f"Processing message for {db_type} channel, user: {message.author.name}")

            thread = None
            mode = None
            query = message.content

            if db_type == 'grok4' and message.content.startswith('!grok'):
                parts = message.content.split(' ', 2)
                if len(parts) > 1 and parts[1] in ['deepsearch', 'deepersearch', 'think']:
                    mode = parts[1]
                    query = parts[2] if len(parts) > 2 else ""
                else:
                    query = message.content[6:].strip() if len(parts) > 1 else ""
            elif db_type == 'gpt' and message.content.startswith('!gpt'):
                if message.content.startswith('!gpt retrieve'):
                    parts = message.content.split(' ', 2)
                    if len(parts) < 3:
                        await message.channel.send("❌ Vui lòng cung cấp batch ID: `!gpt retrieve <batch_id>`")
                        return
                    batch_id = parts[2].strip()
                    job = get_gpt_batch_job(batch_id)
                    if not job:
                        await message.channel.send(f"❌ Batch ID {batch_id} không tồn tại.")
                        return
                    if job['status'] == 'pending':
                        await message.channel.send(f"Batch job {batch_id} vẫn đang xử lý. Vui lòng kiểm tra lại sau.")
                        return
                    elif job['status'] == 'completed' or job['status'] == 'processed':
                        response = job['response_data']
                        try:
                            response_data = json.loads(response)
                            api_response = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                            if api_response:
                                chunks = [api_response[i:i+1900] for i in range(0, len(api_response), 1900)]
                                for i, chunk in enumerate(chunks):
                                    prefix = f"**Batch ID: {batch_id}**\n" if i == 0 else ""
                                    await message.channel.send(f"{prefix}{chunk}")
                                logging.info(f"Retrieved and sent GPT-4.1 response for batch {batch_id} to thread {message.channel.id}")
                            else:
                                await message.channel.send(f"Error: No content in response for batch {batch_id}")
                        except json.JSONDecodeError as e:
                            logging.error(f"Error parsing retrieved GPT-4.1 response for batch {batch_id}: {str(e)}")
                            await message.channel.send(f"Error: Failed to parse response for batch {batch_id}")
                        if job['status'] == 'completed':
                            update_gpt_batch_job(batch_id, "processed", response, datetime.now().isoformat())
                        return
                    else:
                        await message.channel.send(f"Batch job {batch_id} {job['status']}. Không thể lấy phản hồi.")
                        return
                else:
                    query = message.content[5:].strip() if len(message.content) > 5 else ""
                    if not query:
                        await message.channel.send("❌ Vui lòng cung cấp nội dung truy vấn sau `!gpt`.")
                        return
                    file_content = None
                    if message.attachments:
                        for attachment in message.attachments:
                            if attachment.filename.endswith('.txt') or attachment.filename.endswith('.json'):
                                file_content = await attachment.read()
                                file_content = file_content.decode('utf-8')
                                logging.info(f"Read file content from attachment {attachment.filename} for thread {thread.id}")
                    response = await get_gpt_response(thread.id, query, user_id=str(message.author.id), db_type=db_type, file_content=file_content)
            elif db_type == 'gemini' and message.content.startswith('!gemini'):
                query = message.content[8:].strip() if len(message.content) > 8 else ""
            elif db_type == 'general' and message.content.startswith('!general'):
                query = message.content[9:].strip() if len(message.content) > 9 else ""
            elif db_type == 'mental' and message.content.startswith('!mental'):
                query = message.content[8:].strip() if len(message.content) > 8 else ""
            
            if not query and not isinstance(message.channel, discord.Thread):
                await message.channel.send("❌ Vui lòng cung cấp nội dung truy vấn hoặc sử dụng lệnh phù hợp với kênh (ví dụ: `!gpt <nội dung>`).")
                return

            if isinstance(message.channel, discord.Thread):
                thread = message.channel
                logging.info(f"Message in thread {thread.name} (ID: {thread.id}) for {message.author.name}")
            else:
                for t in message.channel.threads:
                    if t.name == thread_name and t.owner_id == message.author.id:
                        thread = t
                        logging.info(f"Found existing thread {t.name} (ID: {t.id}) for {message.author.name}")
                        break

                if not thread:
                    try:
                        logging.info(f"Creating private thread for {message.author.name}")
                        thread = await message.channel.create_thread(
                            name=thread_name,
                            auto_archive_duration=60,
                            type=discord.ChannelType.private_thread,
                            reason=f"Private {db_type} chat for {message.author.name}"
                        )
                        await thread.add_user(message.author)
                        await thread.add_user(bot.user)
                        await message.channel.send(f"✅ {message.author.mention}, tôi đã tạo một thread riêng cho bạn: {thread.mention}. Vui lòng tiếp tục trò chuyện ở đó.")
                        logging.info(f"Created thread {thread.name} (ID: {thread.id}) for {message.author.name}")
                    except discord.errors.Forbidden:
                        logging.error("Bot lacks permission to create threads")
                        await message.channel.send("❌ Không có quyền tạo thread. Vui lòng liên hệ admin.")
                        return
                    except Exception as e:
                        logging.error(f"Error creating thread: {str(e)}")
                        await message.channel.send("❌ Có lỗi khi tạo thread. Vui lòng thử lại.")
                        return

                if not isinstance(message.channel, discord.Thread):
                    logging.info(f"Redirected user {message.author.name} to thread {thread.id}, skipping main channel processing")
                    await asyncio.sleep(1)
                    return

            if is_message_exists(message.id, db_type):
                logging.info(f"Message {message.id} already processed, skipping")
                return

            logging.info(f"Processing message in thread {thread.id} for {db_type}, content: {query[:50]}...")
            try:
                add_message(thread_id=thread.id, message_id=message.id, role="user", content=query, db_type=db_type, mode=mode, user_id=str(message.author.id), batch_id=None)
                if db_type == 'grok4':
                    response = await get_xai_response(thread.id, query, user_id=str(message.author.id), mode=mode)
                elif db_type == 'gpt':
                    response = await get_gpt_response(thread.id, query, user_id=str(message.author.id), db_type=db_type)
                elif db_type == 'gemini':
                    response = await get_gemini_response(thread.id, query, db_type=db_type)
                else:
                    rag_instance = mental_rag if db_type == 'mental' else None
                    response = await get_groq_response(thread.id, query, rag_instance, db_type=db_type)
                logging.info(f"Generated response for thread {thread.id}: {response[:100]}...")

                chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
                for i, chunk in enumerate(chunks):
                    prefix = f"**Mode: {mode or 'default'}**\n" if i == 0 and mode else ""
                    await thread.send(f"{prefix}{chunk}")
                logging.info(f"Sent response in {len(chunks)} chunks to thread {thread.id}")

            except discord.errors.HTTPException as e:
                logging.error(f"Discord API error in thread {thread.id}: {str(e)}")
                await thread.send("❌ Đã có lỗi khi gửi tin nhắn. Vui lòng thử lại.")
            except Exception as e:
                logging.error(f"Error processing message in thread {thread.id}: {str(e)}")
                await thread.send("❌ Đã có lỗi xảy ra khi xử lý tin nhắn. Vui lòng thử lại.")
        elif message.channel.id == NEWS_CHANNEL_ID:
            logging.debug("Ignoring message in news channel")
            pass
        else:
            logging.debug(f"Processing commands for message in channel {message.channel.id}")
            try:
                await bot.process_commands(message)
            except Exception as e:
                logging.error(f"Error processing command in channel {message.channel.id}: {str(e)}")

    @bot.event
    async def on_member_join(member):
        channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            try:
                await channel.send(f"Chào mừng {member.mention} đến với server!")
                logging.info(f"Sent welcome message for {member.name} (ID: {member.id})")
            except Exception as e:
                logging.error(f"Error sending welcome message for {member.name}: {str(e)}")
        else:
            logging.warning(f"Welcome channel {WELCOME_CHANNEL_ID} not found")

    @bot.event
    async def on_voice_state_update(member, before, after):
        if member == bot.user:
            return

        if before.channel and bot.user.id in [m.id for m in before.channel.members]:
            human_members = [m for m in before.channel.members if not m.bot]
            if len(human_members) == 0:
                voice_client = discord.utils.get(bot.voice_clients, channel=before.channel)
                if voice_client:
                    await asyncio.sleep(60)
                    human_members = [m for m in before.channel.members if not m.bot]
                    if len(human_members) == 0:
                        try:
                            await voice_client.disconnect()
                            logging.info(f"Disconnected from empty voice channel in guild {before.channel.guild.id}")
                        except Exception as e:
                            logging.error(f"Error disconnecting from voice channel: {str(e)}")

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Thiếu thông số cần thiết. Hãy dùng `!help` để xem chi tiết.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Tham số sai. Vui lòng kiểm tra lại.")
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send("❌ Lệnh không tồn tại. Hãy thử dùng `!help` để xem danh sách lệnh.")
        elif isinstance(error, asyncio.TimeoutError):
            await ctx.send("⏰ Lệnh bị timeout. Vui lòng thử lại sau.")
            logging.error(f"Command timeout error: {str(error)}")
        else:
            await ctx.send("❌ Đã có lỗi xảy ra.")
            logging.error(f"Unknown command error: {str(error)}")