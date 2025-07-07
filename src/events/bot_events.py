import discord
from discord.ext import commands
import logging
import asyncio
from config import MENTAL_CHANNEL_ID, GENERAL_CHANNEL_ID, WELCOME_CHANNEL_ID, NEWS_CHANNEL_ID
from database import get_history, add_message, get_queue
from src.utils.helpers import get_groq_response, mental_rag
from src.utils.news import news_task

def setup_events(bot, queues, loop_status):
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
        logging.info("Started news task")

    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            logging.debug(f"Ignoring message from bot itself: {message.author}")
            return

        logging.info(f"Received message from {message.author.name} (ID: {message.author.id}) in channel/thread {message.channel.id}")

        # Kiểm tra cả kênh chính và thread thuộc kênh
        parent_channel_id = message.channel.parent_id if isinstance(message.channel, discord.Thread) else message.channel.id
        if parent_channel_id in [MENTAL_CHANNEL_ID, GENERAL_CHANNEL_ID]:
            db_type = 'mental' if parent_channel_id == MENTAL_CHANNEL_ID else 'general'
            thread_name = f"{message.author.name}-private-{db_type}-chat"
            logging.info(f"Processing message for {db_type} channel, user: {message.author.name}")

            thread = None
            if isinstance(message.channel, discord.Thread):
                thread = message.channel
                logging.info(f"Message in thread {thread.name} (ID: {thread.id}) for {message.author.name}")
            else:
                for t in message.channel.threads:
                    if t.name == thread_name and t.owner_id == message.author.id:
                        thread = t
                        logging.info(f"Found existing thread {thread.name} (ID: {thread.id}) for {message.author.name}")
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
                        await thread.add_user(bot.user)  # Thêm bot vào thread
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
                    logging.info(f"Message sent in main channel, redirecting {message.author.name} to thread {thread.id}")
                    try:
                        await message.channel.send(f"📨 {message.author.mention}, hãy gửi tin nhắn trong {thread.mention} để trò chuyện riêng tư.")
                    except Exception as e:
                        logging.error(f"Error sending redirect message to {message.author.name}: {str(e)}")
                    return

            logging.info(f"Processing message in thread {thread.id} for {db_type}, content: {message.content[:50]}...")
            try:
                add_message(thread.id, message.id, "user", message.content, db_type=db_type)
                rag_instance = mental_rag if db_type == 'mental' else None
                response = await get_groq_response(thread.id, message.content, rag_instance, db_type=db_type)
                logging.info(f"Generated response for thread {thread.id}: {response[:100]}...")

                if len(response) <= 2000:
                    await thread.send(response)
                else:
                    chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                    for chunk in chunks:
                        await thread.send(chunk)
                    logging.info(f"Sent response in {len(chunks)} chunks to thread {thread.id}")
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