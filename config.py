import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Load configuration from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
try:
    MENTAL_CHANNEL_ID = int(os.getenv('MENTAL_CHANNEL_ID'))
    GENERAL_CHANNEL_ID = int(os.getenv('GENERAL_CHANNEL_ID'))
    WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID'))
except (TypeError, ValueError):
    raise ValueError("MENTAL_CHANNEL_ID, GENERAL_CHANNEL_ID, and WELCOME_CHANNEL_ID must be valid numbers")