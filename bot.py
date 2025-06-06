import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import sqlite3
import requests
import json
import logging
import yt_dlp
import asyncio

# Load .env file
load_dotenv()

# Set up logging to local file
logging.basicConfig(filename=r'f:\yoombot\bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
try:
    CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
    WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID'))
except (TypeError, ValueError):
    raise ValueError("CHANNEL_ID and WELCOME_CHANNEL_ID must be valid numbers")

# Initialize SQLite databases for chat history and music queues
def init_db():
    # Chat history database
    conn = sqlite3.connect(r'f:\yoombot\chat_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, channel_id TEXT, message_id TEXT, role TEXT, content TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

    # Music queue database
    conn = sqlite3.connect(r'f:\yoombot\queues.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS queues
                 (id INTEGER PRIMARY KEY, guild_id TEXT, url TEXT, audio_url TEXT, title TEXT, position INTEGER)''')
    conn.commit()
    conn.close()

# Add message to chat history
def add_message(channel_id, message_id, role, content):
    conn = sqlite3.connect(r'f:\yoombot\chat_history.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (channel_id, message_id, role, content, timestamp) VALUES (?, ?, ?, ?, datetime('now'))",
              (str(channel_id), str(message_id), role, content))
    conn.commit()
    conn.close()

# Retrieve chat history
def get_history(channel_id, limit=10):
    conn = sqlite3.connect(r'f:\yoombot\chat_history.db')
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE channel_id = ? ORDER BY timestamp DESC LIMIT ?", (str(channel_id), limit))
    history = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
    conn.close()
    return history[::-1]  # Reverse to chronological order

# Add song to queue database
def add_to_queue(guild_id, url, audio_url, title):
    conn = sqlite3.connect(r'f:\yoombot\queues.db')
    c = conn.cursor()
    c.execute("SELECT MAX(position) FROM queues WHERE guild_id = ?", (str(guild_id),))
    max_position = c.fetchone()[0]
    position = (max_position + 1) if max_position is not None else 0
    c.execute("INSERT INTO queues (guild_id, url, audio_url, title, position) VALUES (?, ?, ?, ?, ?)",
              (str(guild_id), url, audio_url, title, position))
    conn.commit()
    conn.close()

# Retrieve queue from database
def get_queue(guild_id):
    conn = sqlite3.connect(r'f:\yoombot\queues.db')
    c = conn.cursor()
    c.execute("SELECT url, audio_url, title FROM queues WHERE guild_id = ? ORDER BY position", (str(guild_id),))
    queue = [(row[0], row[1], row[2]) for row in c.fetchall()]
    conn.close()
    return queue

# Remove song from queue
def remove_from_queue(guild_id, position):
    conn = sqlite3.connect(r'f:\yoombot\queues.db')
    c = conn.cursor()
    c.execute("DELETE FROM queues WHERE guild_id = ? AND position = ?", (str(guild_id), position))
    c.execute("UPDATE queues SET position = position - 1 WHERE guild_id = ? AND position > ?", (str(guild_id), position))
    conn.commit()
    conn.close()

# Clear queue for a guild
def clear_queue(guild_id):
    conn = sqlite3.connect(r'f:\yoombot\queues.db')
    c = conn.cursor()
    c.execute("DELETE FROM queues WHERE guild_id = ?", (str(guild_id),))
    conn.commit()
    conn.close()

def get_groq_response(channel_id, message):
    history = get_history(channel_id)
    history.append({"role": "user", "content": message})
    full_history = [{"role": "system", "content": "You are a helpful assistant. Keep responses concise, under 1500 characters."}] + history
    url = "https://api.groq.com/openai/v1/chat/completions"  # Corrected endpoint
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": full_history,
        "max_tokens": 1500,
        "stream": False
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        api_response = response.json()["choices"][0]["message"]["content"]
        add_message(channel_id, None, "assistant", api_response)
        return api_response
    except requests.exceptions.RequestException as e:
        logging.error(f"Groq API error: {str(e)}")
        return f"Error calling Groq API: {str(e)}"

# Discord bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary để lưu trữ queue nhạc trong bộ nhớ (đồng bộ với database)
queues = {}

# Sự kiện khi bot sẵn sàng
@bot.event
async def on_ready():
    print(f'{bot.user} đã kết nối với Discord!')
    init_db()  # Initialize databases
    for guild in bot.guilds:
        guild_id = str(guild.id)
        queues[guild_id] = get_queue(guild_id)
    logging.info("Bot started, databases initialized, and queues loaded")

# Xử lý tin nhắn cho chatbot
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.id == CHANNEL_ID:
        add_message(message.channel.id, message.id, "user", message.content)
        response = get_groq_response(message.channel.id, message.content)
        if len(response) > 2000:
            response = response[:1997] + "..."
        await message.channel.send(response)
    await bot.process_commands(message)

# Thông báo thành viên mới
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        await channel.send(f'Chào mừng {member.mention} đến với server!')
        logging.info(f"Welcome message sent for {member.name}")

# Lệnh tham gia kênh voice
@bot.command(name='join', help='Tham gia kênh voice của người dùng')
async def join(ctx):
    if ctx.author.voice is None:
        await ctx.send('Bạn chưa ở trong kênh voice.')
        return
    channel = ctx.author.voice.channel
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()
    await ctx.send('Đã tham gia kênh voice.')
    logging.info(f"Joined voice channel {channel.name}")

# Lệnh phát nhạc
@bot.command(name='play', help='Thêm bài hát vào queue và phát nếu chưa có bài nào đang phát')
async def play(ctx, url: str):
    global queues
    guild_id = str(ctx.guild.id)
    if guild_id not in queues:
        queues[guild_id] = []

    ydl_opts = {
        'format': 'bestaudio[acodec=mp3]/bestaudio',
        'noplaylist': True,
        'cachedir': r'f:\yoombot\yt_dlp_cache',
        'socket_timeout': 10,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            title = info.get('title', 'Unknown')
            queues[guild_id].append((url, audio_url, title))
            add_to_queue(guild_id, url, audio_url, title)
            await ctx.send(f'Đã thêm vào queue: {title}')
            logging.info(f"Added to queue: {title} for guild {guild_id}")
    except Exception as e:
        await ctx.send(f'Lỗi khi thêm {url} vào queue: {e}')
        logging.error(f"Error adding {url} to queue: {e}")
        return

    voice_client = ctx.voice_client
    if voice_client is None:
        if ctx.author.voice is None:
            await ctx.send("Bạn chưa ở trong kênh voice.")
            return
        else:
            voice_client = await ctx.author.voice.channel.connect()

    if not voice_client.is_playing():
        await play_next(ctx, voice_client)

# Hàm phát bài hát tiếp theo
async def play_next(ctx, voice_client):
    guild_id = str(ctx.guild.id)
    queue = queues.get(guild_id, [])
    if len(queue) == 0:
        return
    url, audio_url, title = queue.pop(0)
    remove_from_queue(guild_id, 0)
    try:
        ffmpeg_options = {
            'options': '-reconnect 1 -reconnect_streamed 1 -bufsize 64k'
        }
        def after_playing(error):
            if error:
                print(f'Lỗi: {error}')
                logging.error(f"Playback error: {error}")
            bot.loop.call_soon_threadsafe(asyncio.create_task, play_next(ctx, voice_client))
        voice_client.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options), after=after_playing)
        await ctx.send(f'Đang phát: {title}')
        logging.info(f"Playing: {title} for guild {guild_id}")
    except Exception as e:
        await ctx.send(f'Lỗi khi phát {title}: {e}')
        logging.error(f"Error playing {title}: {e}")
        await play_next(ctx, voice_client)

# Lệnh hiển thị queue
@bot.command(name='queue', help='Hiển thị danh sách queue nhạc hiện tại')
async def show_queue(ctx):
    guild_id = str(ctx.guild.id)
    queue = queues.get(guild_id, [])
    if len(queue) == 0:
        await ctx.send('Queue hiện tại đang trống.')
    else:
        queue_list = '\n'.join([f'{i+1}. {title}' for i, (url, audio_url, title) in enumerate(queue)])
        await ctx.send(f'Danh sách queue:\n{queue_list}')
        logging.info(f"Displayed queue for guild {guild_id}")

# Lệnh dừng nhạc
@bot.command(name='stop', help='Dừng phát nhạc')
async def stop(ctx):
    voice_client = ctx.voice_client
    if voice_client is None:
        await ctx.send('Chưa kết nối với kênh voice')
        return
    voice_client.stop()
    await ctx.send('Đã dừng nhạc')
    logging.info(f"Stopped music for guild {ctx.guild.id}")

# Lệnh rời kênh voice
@bot.command(name='leave', help='Rời khỏi kênh voice')
async def leave(ctx):
    voice_client = ctx.voice_client
    if voice_client is None:
        await ctx.send('Chưa kết nối với kênh voice')
        return
    clear_queue(str(ctx.guild.id))
    queues[str(ctx.guild.id)] = []
    await voice_client.disconnect()
    await ctx.send('Đã rời khỏi kênh voice')
    logging.info(f"Left voice channel for guild {ctx.guild.id}")

# Chạy bot
bot.run(BOT_TOKEN)