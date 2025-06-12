FROM python:3.11-slim

# Install FFmpeg and dependencies
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY requirements.txt .
COPY bot.py .
COPY config.py .
COPY database.py .
COPY music_player.py .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create persistent volume directory
RUN mkdir -p /data/yt_dlp_cache

# Run the bot
CMD ["python", "bot.py"]