import sqlite3

def init_db():
    """Khởi tạo tất cả các cơ sở dữ liệu và bảng cần thiết."""
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

    # News articles database
    conn = sqlite3.connect(r'.\data\news.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news_articles
                 (id INTEGER PRIMARY KEY, article_id TEXT UNIQUE, title TEXT, published DATETIME)''')
    conn.commit()
    conn.close()

    # Pixiv priorities database
    conn = sqlite3.connect(r'.\data\pixiv.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pixiv_priorities
                 (type TEXT, value TEXT, PRIMARY KEY (type, value))''')
    conn.commit()
    conn.close()

    # X users database
    conn = sqlite3.connect(r'.\data\x_users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS x_users
                 (username TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

    # Reddit priorities database
    conn = sqlite3.connect(r'.\data\reddit.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reddit_priorities
                 (type TEXT, value TEXT, PRIMARY KEY (type, value))''')
    conn.commit()
    conn.close()

def get_db_connection(db_name="queues.db"):
    """Trả về kết nối đến cơ sở dữ liệu được chỉ định."""
    return sqlite3.connect(rf'.\data\{db_name}')

def clear_mental_chat_history():
    """Xóa lịch sử trò chuyện sức khỏe tinh thần."""
    conn = sqlite3.connect(r'.\data\mental_chat_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, channel_id TEXT, message_id TEXT, role TEXT, content TEXT, timestamp DATETIME)''')
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

def clear_general_chat_history():
    """Xóa lịch sử trò chuyện chung."""
    conn = sqlite3.connect(r'.\data\general_chat_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, channel_id TEXT, message_id TEXT, role TEXT, content TEXT, timestamp DATETIME)''')
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

def clear_music_queue():
    """Xóa hàng đợi nhạc."""
    conn = sqlite3.connect(r'.\data\queues.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS queues
                 (id INTEGER PRIMARY KEY, guild_id TEXT, url TEXT, audio_url TEXT, title TEXT, duration INTEGER, position INTEGER)''')
    c.execute("DELETE FROM queues")
    conn.commit()
    conn.close()

def clear_news_articles():
    """Xóa bài viết tin tức."""
    conn = sqlite3.connect(r'.\data\news.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news_articles
                 (id INTEGER PRIMARY KEY, article_id TEXT UNIQUE, title TEXT, published DATETIME)''')
    c.execute("DELETE FROM news_articles")
    conn.commit()
    conn.close()

def clear_x_users():
    """Xóa danh sách người dùng X được theo dõi."""
    conn = sqlite3.connect(r'.\data\x_users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS x_users
                 (username TEXT PRIMARY KEY)''')
    c.execute("DELETE FROM x_users")
    conn.commit()
    conn.close()

def clear_reddit_priorities():
    """Xóa danh sách ưu tiên Reddit."""
    conn = sqlite3.connect(r'.\data\reddit.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reddit_priorities
                 (type TEXT, value TEXT, PRIMARY KEY (type, value))''')
    c.execute("DELETE FROM reddit_priorities")
    conn.commit()
    conn.close()

def add_message(channel_id, message_id, role, content, db_type):
    """Thêm tin nhắn vào lịch sử trò chuyện."""
    db_path = r'.\data\mental_chat_history.db' if db_type == 'mental' else r'.\data\general_chat_history.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO messages (channel_id, message_id, role, content, timestamp) VALUES (?, ?, ?, ?, datetime('now'))",
              (str(channel_id), str(message_id), role, content))
    conn.commit()
    conn.close()

def get_history(channel_id, limit=20, db_type='mental'):
    """Lấy lịch sử trò chuyện."""
    db_path = r'.\data\mental_chat_history.db' if db_type == 'mental' else r'.\data\general_chat_history.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE channel_id = ? ORDER BY timestamp ASC LIMIT ?",
              (str(channel_id), limit))
    history = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
    conn.close()
    return history

def add_news_article(article_id, title, published):
    """Thêm bài viết tin tức."""
    conn = sqlite3.connect(r'.\data\news.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO news_articles (article_id, title, published) VALUES (?, ?, ?)",
                  (article_id, title, published))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Article already exists
    conn.close()

def is_article_sent(article_id):
    """Kiểm tra xem bài viết đã được gửi chưa."""
    conn = sqlite3.connect(r'.\data\news.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM news_articles WHERE article_id = ?", (article_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def add_to_queue(guild_id, url, audio_url, title, duration=0):
    """Thêm bài hát vào hàng đợi."""
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
    """Lấy hàng đợi theo guild_id."""
    conn = sqlite3.connect(r'.\data\queues.db')
    c = conn.cursor()
    c.execute("SELECT url, audio_url, title, duration FROM queues WHERE guild_id = ? ORDER BY position", (str(guild_id),))
    queue = [(row[0], row[1], row[2], row[3] or 0) for row in c.fetchall()]
    conn.close()
    return queue

def remove_from_queue(guild_id, position):
    """Xóa bài hát khỏi hàng đợi theo vị trí."""
    conn = sqlite3.connect(r'.\data\queues.db')
    c = conn.cursor()
    c.execute("DELETE FROM queues WHERE guild_id = ? AND position = ?", (str(guild_id), position))
    c.execute("UPDATE queues SET position = position - 1 WHERE guild_id = ? AND position > ?", (str(guild_id), position))
    conn.commit()
    conn.close()

def clear_queue(guild_id):
    """Xóa toàn bộ hàng đợi của guild_id."""
    conn = sqlite3.connect(r'.\data\queues.db')
    c = conn.cursor()
    c.execute("DELETE FROM queues WHERE guild_id = ?", (str(guild_id),))
    conn.commit()
    conn.close()