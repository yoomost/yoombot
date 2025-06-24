import sqlite3

def init_db():
    # Mental health chat history database
    conn = sqlite3.connect(r'.\data\mental_chat_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, channel_id TEXT, message_id TEXT, role TEXT, content TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

    # General chat history database
    conn = sqlite3.connect(r'.\data\general_chat_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, channel_id TEXT, message_id TEXT, role TEXT, content TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

    # Music queue database
    conn = sqlite3.connect(r'.\data\queues.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS queues
                 (id INTEGER PRIMARY KEY, guild_id TEXT, url TEXT, audio_url TEXT, title TEXT, duration INTEGER, position INTEGER)''')
    conn.commit()
    conn.close()

def clear_mental_chat_history():
    conn = sqlite3.connect(r'.\data\mental_chat_history.db')
    c = conn.cursor()
    # Ensure table exists
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, channel_id TEXT, message_id TEXT, role TEXT, content TEXT, timestamp DATETIME)''')
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

def clear_general_chat_history():
    conn = sqlite3.connect(r'.\data\general_chat_history.db')
    c = conn.cursor()
    # Ensure table exists
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, channel_id TEXT, message_id TEXT, role TEXT, content TEXT, timestamp DATETIME)''')
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

def clear_music_queue():
    conn = sqlite3.connect(r'.\data\queues.db')
    c = conn.cursor()
    # Ensure table exists
    c.execute('''CREATE TABLE IF NOT EXISTS queues
                 (id INTEGER PRIMARY KEY, guild_id TEXT, url TEXT, audio_url TEXT, title TEXT, duration INTEGER, position INTEGER)''')
    c.execute("DELETE FROM queues")
    conn.commit()
    conn.close()

def add_message(channel_id, message_id, role, content, db_type):
    db_path = r'.\data\mental_chat_history.db' if db_type == 'mental' else r'.\data\general_chat_history.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO messages (channel_id, message_id, role, content, timestamp) VALUES (?, ?, ?, ?, datetime('now'))",
              (str(channel_id), str(message_id), role, content))
    conn.commit()
    conn.close()

def get_history(channel_id, limit=20, db_type='mental'):
    db_path = r'.\data\mental_chat_history.db' if db_type == 'mental' else r'.\data\general_chat_history.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE channel_id = ? ORDER BY timestamp ASC LIMIT ?",
              (str(channel_id), limit))
    history = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
    conn.close()
    return history

def add_to_queue(guild_id, url, audio_url, title, duration=0):
    conn = sqlite3.connect(r'.\data\queues.db')
    c = conn.cursor()
    c.execute("SELECT MAX(position) FROM queues WHERE guild_id = ?", (str(guild_id),))
    max_position = c.fetchone()[0]
    position = (max_position + 1) if max_position is not None else 0
    c.execute("INSERT INTO queues (guild_id, url, audio_url, title, duration, position) VALUES (?, ?, ?, ?, ?, ?)",
              (str(guild_id), url, audio_url, title, duration, position))
    conn.commit()
    conn.close()

def get_queue(guild_id):
    conn = sqlite3.connect(r'.\data\queues.db')
    c = conn.cursor()
    c.execute("SELECT url, audio_url, title, duration FROM queues WHERE guild_id = ? ORDER BY position", (str(guild_id),))
    queue = [(row[0], row[1], row[2], row[3] or 0) for row in c.fetchall()]
    conn.close()
    return queue

def remove_from_queue(guild_id, position):
    conn = sqlite3.connect(r'.\data\queues.db')
    c = conn.cursor()
    c.execute("DELETE FROM queues WHERE guild_id = ? AND position = ?", (str(guild_id), position))
    c.execute("UPDATE queues SET position = position - 1 WHERE guild_id = ? AND position > ?", (str(guild_id), position))
    conn.commit()
    conn.close()

def clear_queue(guild_id):
    conn = sqlite3.connect(r'.\data\queues.db')
    c = conn.cursor()
    c.execute("DELETE FROM queues WHERE guild_id = ?", (str(guild_id),))
    conn.commit()
    conn.close()