import discord
from discord.ext import commands
import logging
import asyncio
from config import CHANNEL_ID, WELCOME_CHANNEL_ID
from database import get_history, add_message, get_queue
from src.utils.helpers import get_groq_response

def setup_events(bot, queues, loop_status):
    @bot.event
    async def on_ready():
        print(f'{bot.user} đã kết nối với Discord!')
        for guild in bot.guilds:
            guild_id = str(guild.id)
            queues[guild_id] = get_queue(guild_id)
        await bot.tree.sync()
        logging.info("Bot started, queues loaded, and slash commands synced")

    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            return
        if message.channel.id == CHANNEL_ID:
            add_message(message.channel.id, message.id, "user", message.content)
            response = await get_groq_response(message.channel.id, message.content)
            if len(response) <= 2000:
                await message.channel.send(response)
            else:
                chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                for chunk in chunks:
                    await message.channel.send(chunk)
        await bot.process_commands(message)

    @bot.event
    async def on_member_join(member):
        channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            await channel.send(f'Chào mừng {member.mention} đến với server!')
            logging.info(f"Welcome message sent for {member.name}")

    @bot.event
    async def on_voice_state_update(member, before, after):
        if member == bot.user:
            return
        
        if before.channel and bot.user in before.channel.members:
            human_members = [m for m in before.channel.members if not m.bot]
            if len(human_members) == 0:
                voice_client = discord.utils.get(bot.voice_clients, guild=before.channel.guild)
                if voice_client:
                    await asyncio.sleep(30)
                    human_members = [m for m in before.channel.members if not m.bot]
                    if len(human_members) == 0:
                        await voice_client.disconnect()
                        logging.info(f"Disconnected from empty voice channel in guild {before.channel.guild.id}")

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('❌ Thiếu tham số bắt buộc. Sử dụng `!help` để xem hướng dẫn.')
        elif isinstance(error, commands.BadArgument):
            await ctx.send('❌ Tham số không hợp lệ. Vui lòng kiểm tra lại.')
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send('❌ Lệnh không tồn tại. Sử dụng `!help` để xem danh sách lệnh.')
        elif isinstance(error, commands.CommandInvokeError):
            if "TimeoutError" in str(error):
                await ctx.send('⏰ Lệnh bị timeout. Vui lòng thử lại sau.')
            else:
                await ctx.send(f'❌ Đã xảy ra lỗi khi thực hiện lệnh.')
            logging.error(f"Command error: {error}")
        else:
            await ctx.send(f'❌ Đã xảy ra lỗi không xác định.')
            logging.error(f"Unhandled error: {error}")