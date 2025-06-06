import sqlite3

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

def add_message(channel_id, message_id, role, content):
    conn = sqlite3.connect(r'f:\yoombot\chat_history.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (channel_id, message_id, role, content, timestamp) VALUES (?, ?, ?, ?, datetime('now'))",
              (str(channel_id), str(message_id), role, content))
    conn.commit()
    conn.close()

def get_history(channel_id, limit=10):
    conn = sqlite3.connect(r'f:\yoombot\chat_history.db')
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE channel_id = ? ORDER BY timestamp DESC LIMIT ?", (str(channel_id), limit))
    history = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
    conn.close()
    return history[::-1]  # Reverse to chronological order

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

def get_queue(guild_id):
    conn = sqlite3.connect(r'f:\yoombot\queues.db')
    c = conn.cursor()
    c.execute("SELECT url, audio_url, title FROM queues WHERE guild_id = ? ORDER BY position", (str(guild_id),))
    queue = [(row[0], row[1], row[2]) for row in c.fetchall()]
    conn.close()
    return queue

def remove_from_queue(guild_id, position):
    conn = sqlite3.connect(r'f:\yoombot\queues.db')
    c = conn.cursor()
    c.execute("DELETE FROM queues WHERE guild_id = ? AND position = ?", (str(guild_id), position))
    c.execute("UPDATE queues SET position = position - 1 WHERE guild_id = ? AND position > ?", (str(guild_id), position))
    conn.commit()
    conn.close()

def clear_queue(guild_id):
    conn = sqlite3.connect(r'f:\yoombot\queues.db')
    c = conn.cursor()
    c.execute("DELETE FROM queues WHERE guild_id = ?", (str(guild_id),))
    conn.commit()
    conn.close()