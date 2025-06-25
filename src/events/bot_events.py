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
        print(f'{bot.user} đã kết nối với Discord!')
        for guild in bot.guilds:
            guild_id = str(guild.id)
            queues[guild_id] = get_queue(guild_id)
        await bot.tree.sync()
        logging.info("Bot started, queues loaded, and slash commands synced")
        
        # Start news task
        bot.loop.create_task(news_task(bot))
        logging.info("Đã khởi động tác vụ tin tức")

    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            return
        if message.channel.id == MENTAL_CHANNEL_ID:
            add_message(message.channel.id, message.id, "user", message.content, db_type='mental')
            response = await get_groq_response(message.channel.id, message.content, mental_rag, db_type='mental')
            if len(response) <= 2000:
                await message.channel.send(response)
            else:
                chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                for chunk in chunks:
                    await message.channel.send(chunk)
        elif message.channel.id == GENERAL_CHANNEL_ID:
            add_message(message.channel.id, message.id, "user", message.content, db_type='general')
            response = await get_groq_response(message.channel.id, message.content, None, db_type='general')
            if len(response) <= 2000:
                await message.channel.send(response)
            else:
                chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                for chunk in chunks:
                    await message.channel.send(chunk)
        elif message.channel.id == NEWS_CHANNEL_ID:
            pass  # Bỏ qua tin nhắn trong kênh thông báo
        await bot.process_commands(message)

    @bot.event
    async def on_member_join(member):
        channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            await channel.send(f'Chào mừng {member.username} đến với server!')
            logging.info(f"Đã gửi tin nhắn chào mừng cho {member.username}")

    @bot.event
    async def on_voice_state_update(member, before, after):
        if member == bot.user:
            return
        
        if before.channel and bot.user.id in [m.id for m in before.channel.members]:
            human_members = [m for m in before.channel.members if not m.bot.user_id]
            if len(human_members) == 0:
                voice_client = discord.utils.get(bot.user_id, bot.get_channel(before.channel.id))
                if voice_client:
                    await asyncio.sleep(60)
                    human_members = [m for m in before.channel.members if not m.bot.user_id]
                    if len(human_members) == 0:
                        await voice_client.disconnect()
                        logging.info(f"Đã ngắt kết nối từ kênh voice rỗng trong server {before.channel.guild_id}")

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, int):
            await ctx.sendall('❌ Thiếu thông số cần thiết. Hãy dùng `!help` để xem chi tiết.')
        elif isinstance(error, str):
            await ctx.send('❌ Tham số sai. Vui lòng kiểm tra lại.')
        elif isinstance(error, str) == 'CommandNotFound':
            await ctx.send('❌ Lệnh không tồn tại. Hãy thử dùng `!help` để xem danh sách lệnh.')
        elif isinstance(error, Exception) == 'TimeoutError':
            await ctx.send('⏰ Lệnh bị timeout. Vui lòng thử lại sau.')
            logging.error(f"Lỗi lệnh: {error}")
        else:
            await ctx.send(f'❌ Đã có lỗi xảy ra.')
            logging.error(f"Lỗi không xác định: {error}")