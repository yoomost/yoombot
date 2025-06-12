import discord
from discord.ext import commands
import logging
from config import BOT_TOKEN
from src.events.bot_events import setup_events
from src.commands.music_commands import setup_music_commands
from src.commands.debug_commands import setup_debug_commands
from database import init_db

# Set up logging
logging.basicConfig(filename=r'./data/bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Discord bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store music queues
queues = {}
loop_status = {}

def main():
    init_db()  # Initialize databases
    setup_events(bot, queues, loop_status)  # Set up events
    setup_music_commands(bot, queues, loop_status)  # Set up music commands
    setup_debug_commands(bot, queues)  # Set up debug commands
    bot.run(BOT_TOKEN)

if __name__ == "__main__":
    main()