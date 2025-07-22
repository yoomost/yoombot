import os
import sys
from dotenv import load_dotenv
import logging

def get_base_path():
    """Get the base path for bundled or development environment."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller executable
        return sys._MEIPASS
    else:
        # Running as a regular Python script
        return os.path.dirname(os.path.abspath(__file__))

# Load .env file from the correct path
env_path = os.path.join(get_base_path(), ".env")
if not os.path.exists(env_path):
    error_msg = f".env file not found at {env_path}. Ensure it is included in the project root or PyInstaller bundle."
    logging.error(error_msg)
    raise FileNotFoundError(error_msg)

# Read .env file contents for debugging
try:
    with open(env_path, 'r', encoding='utf-8') as f:
        env_contents = f.read()
    logging.debug(f".env file contents:\n{env_contents}")
except Exception as e:
    logging.error(f"Error reading .env file at {env_path}: {str(e)}")
    raise

# Load .env file
load_dotenv(env_path)
logging.info(f"Loaded .env file from {env_path}")

# Log all environment variables for debugging
logging.debug(f"Environment variables after loading .env: {dict(os.environ)}")

# Load configuration from environment variables
required_vars = [
    'BOT_TOKEN', 'GROQ_API_KEY', 'XAI_API_KEY', 'PIXIV_REFRESH_TOKEN',
    'REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_USER_AGENT',
    'MENTAL_CHANNEL_ID', 'GENERAL_CHANNEL_ID', 'WELCOME_CHANNEL_ID',
    'WIKI_CHANNEL_ID', 'EDUCATIONAL_CHANNEL_ID', 'NEWS_CHANNEL_ID',
    'IMAGE_CHANNEL_ID', 'GROK4_CHANNEL_ID', 'ADMIN_ROLE_ID', 'GEMINI_API_KEY' # Thêm GEMINI_API_KEY
]

missing_vars = [var for var in required_vars if os.getenv(var) is None]
if missing_vars:
    error_msg = f"Missing or invalid environment variables: {', '.join(missing_vars)}"
    logging.error(error_msg)
    raise ValueError(error_msg)

BOT_TOKEN = os.getenv('BOT_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
XAI_API_KEY = os.getenv('XAI_API_KEY')  # API key for Grok 4
PIXIV_REFRESH_TOKEN = os.getenv('PIXIV_REFRESH_TOKEN')
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') # Lấy GEMINI_API_KEY

try:
    MENTAL_CHANNEL_ID = int(os.getenv('MENTAL_CHANNEL_ID'))
    GENERAL_CHANNEL_ID = int(os.getenv('GENERAL_CHANNEL_ID'))
    WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID'))
    WIKI_CHANNEL_ID = int(os.getenv('WIKI_CHANNEL_ID'))
    EDUCATIONAL_CHANNEL_ID = int(os.getenv('EDUCATIONAL_CHANNEL_ID'))
    NEWS_CHANNEL_ID = int(os.getenv('NEWS_CHANNEL_ID'))
    IMAGE_CHANNEL_ID = int(os.getenv('IMAGE_CHANNEL_ID'))
    GROK4_CHANNEL_ID = int(os.getenv('GROK4_CHANNEL_ID'))
    ADMIN_ROLE_ID = int(os.getenv('ADMIN_ROLE_ID'))
    GEMINI_CHANNEL_ID = int(os.getenv('GEMINI_CHANNEL_ID')) # Thêm GEMINI_CHANNEL_ID
except (TypeError, ValueError) as e:
    logging.error(f"Error converting environment variables to integers: {str(e)}")
    raise ValueError("MENTAL_CHANNEL_ID, GENERAL_CHANNEL_ID, WELCOME_CHANNEL_ID, IMAGE_CHANNEL_ID, GROK4_CHANNEL_ID, ADMIN_ROLE_ID and NEWS_CHANNEL_ID must be valid numbers")