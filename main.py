import discord
from discord.ext import commands
import logging
import asyncio
from config import BOT_TOKEN
from src.events.bot_events import setup_events
from src.commands.music_commands import setup_music_commands
from src.commands.debug_commands import setup_debug_commands
from database import init_db, clear_mental_chat_history, clear_general_chat_history, clear_music_queue, clear_news_articles
from src.utils.news import news_task
from src.utils.x_images import x_images_task

# Set up logging
logging.basicConfig(filename=r'.\data\bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Discord bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store music queues
queues = {}
loop_status = {}

@bot.command()
async def add_x_user(ctx, username):
    """Thêm người dùng X để theo dõi ảnh."""
    username = username.replace("@", "")
    from database import get_db_connection
    conn = get_db_connection("x_users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO x_users (username) VALUES (?)", (username,))
    conn.commit()
    conn.close()
    await ctx.send(f"Đã thêm người dùng X: @{username} để theo dõi ảnh.")
    logging.info(f"Đã thêm người dùng X: {username}")

@bot.event
async def on_ready():
    """Xử lý khi bot sẵn sàng."""
    logging.info(f"Bot đã sẵn sàng với tên: {bot.user.name}")
    await setup_tasks()

async def setup_tasks():
    """Khởi tạo các task bất đồng bộ."""
    init_db()
    logging.info("Initialized mental_chat_history.db, general_chat_history.db, queues.db, news.db, and x_users.db")

    try:
        clear_mental_chat_history()
        clear_general_chat_history()
        clear_music_queue()
        clear_news_articles()
        queues.clear()
        loop_status.clear()
        logging.info("Cleared mental chat history, general chat history, music queues, news articles, and in-memory data")
    except Exception as e:
        logging.error(f"Error clearing data on startup: {str(e)}")
        raise

    # Set up bot
    setup_events(bot, queues, loop_status)
    setup_music_commands(bot, queues, loop_status)
    setup_debug_commands(bot, queues)

    # Tạo các task
    bot.loop.create_task(news_task(bot))
    bot.loop.create_task(x_images_task(bot))

async def main():
    """Hàm main bất đồng bộ để chạy bot."""
    async with bot:
        await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())