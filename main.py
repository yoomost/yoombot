import discord
from discord.ext import commands
import logging
import asyncio
from config import BOT_TOKEN
from src.events.bot_events import setup_events
from src.commands.music_commands import setup_music_commands
from src.commands.debug_commands import setup_debug_commands
from src.commands.commands import setup as setup_educational_commands
from database import init_db, get_db_connection, clear_queue, clear_news_articles
from src.utils.news import news_task
from src.utils.pixiv import setup as x_images_setup
from src.utils.reddit import setup as reddit_images_setup

# Set up logging
logging.basicConfig(filename=r'./data/bot.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Discord bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store music queues
queues = {}
loop_status = {}

def clear_music_queue():
    """Xóa toàn bộ hàng đợi nhạc."""
    try:
        conn = get_db_connection("queues.db")
        c = conn.cursor()
        c.execute("DELETE FROM queues")
        conn.commit()
        logging.info("Cleared music queue in queues.db")
    except Exception as e:
        logging.error(f"Error clearing music queue: {str(e)}")
    finally:
        conn.close()

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
    # Clear non-chatbot queues on startup
    clear_music_queue()
    clear_news_articles()
    await setup_tasks()

async def setup_tasks():
    """Khởi tạo các task bất đồng bộ."""
    init_db()
    setup_events(bot, queues, loop_status)
    setup_music_commands(bot, queues, loop_status)
    setup_debug_commands(bot, queues)
    await setup_educational_commands(bot)
    bot.loop.create_task(x_images_setup(bot))
    bot.loop.create_task(reddit_images_setup(bot))
    bot.loop.create_task(news_task(bot))
    logging.info("All tasks and commands set up")

async def main():
    try:
        await bot.start(BOT_TOKEN)
    except Exception as e:
        logging.error(f"Error starting bot: {str(e)}")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())