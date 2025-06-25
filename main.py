import discord
from discord.ext import commands
import logging
import asyncio
from config import BOT_TOKEN
from src.events.bot_events import setup_events
from src.commands.music_commands import setup_music_commands
from src.commands.debug_commands import setup_debug_commands
from database import init_db, clear_mental_chat_history, clear_general_chat_history, clear_music_queue, clear_news_articles

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

async def main():
    # Initialize databases
    init_db()
    logging.info("Initialized mental_chat_history.db, general_chat_history.db, queues.db, and news.db")

    # Clear data on startup
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

    # Start bot
    async with bot:
        await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())