import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Load configuration from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
PIXIV_REFRESH_TOKEN = os.getenv('PIXIV_REFRESH_TOKEN')
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT')
try:
    MENTAL_CHANNEL_ID = int(os.getenv('MENTAL_CHANNEL_ID'))
    GENERAL_CHANNEL_ID = int(os.getenv('GENERAL_CHANNEL_ID'))
    WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID'))
    NEWS_CHANNEL_ID = int(os.getenv('NEWS_CHANNEL_ID'))
    IMAGE_CHANNEL_ID = int(os.getenv('IMAGE_CHANNEL_ID'))
    ADMIN_ROLE_ID = int(os.getenv('ADMIN_ROLE_ID'))
except (TypeError, ValueError):
    raise ValueError("MENTAL_CHANNEL_ID, GENERAL_CHANNEL_ID, WELCOME_CHANNEL_ID, IMAGE_CHANNEL_ID, ADMIN_ROLE_ID and NEWS_CHANNEL_ID must be valid numbers")