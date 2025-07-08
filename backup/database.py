import sqlite3
import logging

def init_db():
    """Khởi tạo tất cả các cơ sở dữ liệu và bảng cần thiết."""
    def ensure_thread_id_column(db_path, table_name):
        """Kiểm tra và thêm cột thread_id nếu chưa tồn tại."""
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(f"PRAGMA table_info({table_name})")
            columns = [info[1] for info in c.fetchall()]
            if 'thread_id' not in columns:
                c.execute(f"ALTER TABLE {table_name} ADD COLUMN thread_id TEXT")
                conn.commit()
                logging.info(f"Added thread_id column to {table_name} in {db_path}")
            conn.close()
        except Exception as e:
            logging.error(f"Error checking/adding thread_id column in {db_path}: {str(e)}")

    try:
        conn = sqlite3.connect(r'.\data\mental_chat_history.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS messages
                     (id INTEGER PRIMARY KEY, thread_id TEXT, message_id TEXT, role TEXT, content TEXT, timestamp DATETIME)''')
        conn.commit()
        logging.info("Initialized mental_chat_history.db")
        ensure_thread_id_column(r'.\data\mental_chat_history.db', 'messages')
    except Exception as e:
        logging.error(f"Error initializing mental_chat_history.db: {str(e)}")
    finally:
        conn.close()

    try:
        conn = sqlite3.connect(r'.\data\general_chat_history.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS messages
                     (id INTEGER PRIMARY KEY, thread_id TEXT, message_id TEXT, role TEXT, content TEXT, timestamp DATETIME)''')
        conn.commit()
        logging.info("Initialized general_chat_history.db")
        ensure_thread_id_column(r'.\data\general_chat_history.db', 'messages')
    except Exception as e:
        logging.error(f"Error initializing general_chat_history.db: {str(e)}")
    finally:
        conn.close()

    try:
        conn = sqlite3.connect(r'.\data\queues.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS queues
                     (id INTEGER PRIMARY KEY, guild_id TEXT, url TEXT, audio_url TEXT, title TEXT, duration INTEGER, position INTEGER)''')
        conn.commit()
        logging.info("Initialized queues.db")
    except Exception as e:
        logging.error(f"Error initializing queues.db: {str(e)}")
    finally:
        conn.close()

    try:
        conn = sqlite3.connect(r'.\data\news.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS news_articles
                     (id INTEGER PRIMARY KEY, article_id TEXT UNIQUE, title TEXT, published DATETIME)''')
        conn.commit()
        logging.info("Initialized news.db")
    except Exception as e:
        logging.error(f"Error initializing news.db: {str(e)}")
    finally:
        conn.close()

    try:
        conn = sqlite3.connect(r'.\data\pixiv.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS pixiv_priorities
                     (type TEXT, value TEXT, PRIMARY KEY (type, value))''')
        conn.commit()
        logging.info("Initialized pixiv.db")
    except Exception as e:
        logging.error(f"Error initializing pixiv.db: {str(e)}")
    finally:
        conn.close()

    try:
        conn = sqlite3.connect(r'.\data\x_users.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS x_users
                     (username TEXT PRIMARY KEY)''')
        conn.commit()
        logging.info("Initialized x_users.db")
    except Exception as e:
        logging.error(f"Error initializing x_users.db: {str(e)}")
    finally:
        conn.close()

    try:
        conn = sqlite3.connect(r'.\data\reddit.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS reddit_priorities
                     (type TEXT, value TEXT, PRIMARY KEY (type, value))''')
        c.execute('''CREATE TABLE IF NOT EXISTS reddit_posts
                     (post_id TEXT PRIMARY KEY, title TEXT, posted_at DATETIME)''')
        conn.commit()
        logging.info("Initialized reddit.db")
    except Exception as e:
        logging.error(f"Error initializing reddit.db: {str(e)}")
    finally:
        conn.close()

def get_db_connection(db_name="queues.db"):
    """Trả về kết nối đến cơ sở dữ liệu được chỉ định."""
    try:
        conn = sqlite3.connect(rf'.\data\{db_name}')
        logging.info(f"Connected to database {db_name}")
        return conn
    except Exception as e:
        logging.error(f"Error connecting to database {db_name}: {str(e)}")
        raise

def clear_mental_chat_history():
    """Xóa lịch sử trò chuyện sức khỏe tinh thần."""
    try:
        conn = sqlite3.connect(r'.\data\mental_chat_history.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS messages
                     (id INTEGER PRIMARY KEY, thread_id TEXT, message_id TEXT, role TEXT, content TEXT, timestamp DATETIME)''')
        c.execute("DELETE FROM messages")
        conn.commit()
        logging.info("Cleared mental_chat_history.db")
    except Exception as e:
        logging.error(f"Error clearing mental_chat_history.db: {str(e)}")
    finally:
        conn.close()

def clear_general_chat_history():
    """Xóa lịch sử trò chuyện chung."""
    try:
        conn = sqlite3.connect(r'.\data\general_chat_history.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS messages
                     (id INTEGER PRIMARY KEY, thread_id TEXT, message_id TEXT, role TEXT, content TEXT, timestamp DATETIME)''')
        c.execute("DELETE FROM messages")
        conn.commit()
        logging.info("Cleared general_chat_history.db")
    except Exception as e:
        logging.error(f"Error clearing general_chat_history.db: {str(e)}")
    finally:
        conn.close()

def clear_music_queue():
    """Xóa hàng đợi nhạc."""
    try:
        conn = sqlite3.connect(r'.\data\queues.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS queues
                     (id INTEGER PRIMARY KEY, guild_id TEXT, url TEXT, audio_url TEXT, title TEXT, duration INTEGER, position INTEGER)''')
        c.execute("DELETE FROM queues")
        conn.commit()
        logging.info("Cleared queues.db")
    except Exception as e:
        logging.error(f"Error clearing queues.db: {str(e)}")
    finally:
        conn.close()

def clear_news_articles():
    """Xóa bài viết tin tức."""
    try:
        conn = sqlite3.connect(r'.\data\news.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS news_articles
                     (id INTEGER PRIMARY KEY, article_id TEXT UNIQUE, title TEXT, published DATETIME)''')
        c.execute("DELETE FROM news_articles")
        conn.commit()
        logging.info("Cleared news.db")
    except Exception as e:
        logging.error(f"Error clearing news.db: {str(e)}")
    finally:
        conn.close()

def clear_x_users():
    """Xóa danh sách người dùng X được theo dõi."""
    try:
        conn = sqlite3.connect(r'.\data\x_users.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS x_users
                     (username TEXT PRIMARY KEY)''')
        c.execute("DELETE FROM x_users")
        conn.commit()
        logging.info("Cleared x_users.db")
    except Exception as e:
        logging.error(f"Error clearing x_users.db: {str(e)}")
    finally:
        conn.close()

def clear_reddit_priorities():
    """Xóa danh sách ưu tiên Reddit."""
    try:
        conn = sqlite3.connect(r'.\data\reddit.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS reddit_priorities
                     (type TEXT, value TEXT, PRIMARY KEY (type, value))''')
        c.execute("DELETE FROM reddit_priorities")
        conn.commit()
        logging.info("Cleared reddit_priorities in reddit.db")
    except Exception as e:
        logging.error(f"Error clearing reddit_priorities: {str(e)}")
    finally:
        conn.close()

def clear_reddit_posts():
    """Xóa danh sách bài viết Reddit đã đăng."""
    try:
        conn = sqlite3.connect(r'.\data\reddit.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS reddit_posts
                     (post_id TEXT PRIMARY KEY, title TEXT, posted_at DATETIME)''')
        c.execute("DELETE FROM reddit_posts")
        conn.commit()
        logging.info("Cleared reddit_posts in reddit.db")
    except Exception as e:
        logging.error(f"Error clearing reddit_posts: {str(e)}")
    finally:
        conn.close()

def add_reddit_post(post_id, title):
    """Thêm bài viết Reddit vào cơ sở dữ liệu."""
    try:
        conn = sqlite3.connect(r'.\data\reddit.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO reddit_posts (post_id, title, posted_at) VALUES (?, ?, datetime('now'))",
                  (post_id, title))
        conn.commit()
        logging.info(f"Added Reddit post {post_id} to reddit.db")
    except Exception as e:
        logging.error(f"Error adding Reddit post {post_id}: {str(e)}")
    finally:
        conn.close()

def is_reddit_post_sent(post_id):
    """Kiểm tra xem bài viết Reddit đã được gửi chưa."""
    try:
        conn = sqlite3.connect(r'.\data\reddit.db')
        c = conn.cursor()
        c.execute("SELECT 1 FROM reddit_posts WHERE post_id = ?", (post_id,))
        exists = c.fetchone() is not None
        conn.close()
        logging.info(f"Checked Reddit post {post_id}: {'sent' if exists else 'not sent'}")
        return exists
    except Exception as e:
        logging.error(f"Error checking Reddit post {post_id}: {str(e)}")
        return False

def add_message(thread_id, message_id, role, content, db_type):
    """Thêm tin nhắn vào lịch sử trò chuyện."""
    db_path = r'.\data\mental_chat_history.db' if db_type == 'mental' else r'.\data\general_chat_history.db'
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT INTO messages (thread_id, message_id, role, content, timestamp) VALUES (?, ?, ?, ?, datetime('now'))",
                  (str(thread_id), str(message_id), role, content))
        conn.commit()
        logging.info(f"Added message to {db_type} database for thread {thread_id}")
    except Exception as e:
        logging.error(f"Error adding message to {db_type} database for thread {thread_id}: {str(e)}")
    finally:
        conn.close()

def get_history(thread_id, limit=20, db_type='mental'):
    """Lấy lịch sử trò chuyện."""
    db_path = r'.\data\mental_chat_history.db' if db_type == 'mental' else r'.\data\general_chat_history.db'
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT role, content FROM messages WHERE thread_id = ? ORDER BY timestamp ASC LIMIT ?",
                  (str(thread_id), limit))
        history = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
        logging.info(f"Retrieved {len(history)} messages from {db_type} database for thread {thread_id}")
        return history
    except Exception as e:
        logging.error(f"Error retrieving history from {db_type} database for thread {thread_id}: {str(e)}")
        return []
    finally:
        conn.close()

def add_news_article(article_id, title, published):
    """Thêm bài viết tin tức."""
    try:
        conn = sqlite3.connect(r'.\data\news.db')
        c = conn.cursor()
        c.execute("INSERT INTO news_articles (article_id, title, published) VALUES (?, ?, ?)",
                  (article_id, title, published))
        conn.commit()
        logging.info(f"Added news article {article_id} to news.db")
    except sqlite3.IntegrityError:
        logging.info(f"News article {article_id} already exists in news.db")
    except Exception as e:
        logging.error(f"Error adding news article {article_id}: {str(e)}")
    finally:
        conn.close()

def is_article_sent(article_id):
    """Kiểm tra xem bài viết đã được gửi chưa."""
    try:
        conn = sqlite3.connect(r'.\data\news.db')
        c = conn.cursor()
        c.execute("SELECT 1 FROM news_articles WHERE article_id = ?", (article_id,))
        exists = c.fetchone() is not None
        conn.close()
        logging.info(f"Checked news article {article_id}: {'sent' if exists else 'not sent'}")
        return exists
    except Exception as e:
        logging.error(f"Error checking news article {article_id}: {str(e)}")
        return False

def add_to_queue(guild_id, url, audio_url, title, duration=0):
    """Thêm bài hát vào hàng đợi."""
    try:
        conn = sqlite3.connect(r'.\data\queues.db')
        c = conn.cursor()
        c.execute("SELECT MAX(position) FROM queues WHERE guild_id = ?", (str(guild_id),))
        max_position = c.fetchone()[0]
        position = (max_position + 1) if max_position is not None else 0
        c.execute("INSERT INTO queues (guild_id, url, audio_url, title, duration, position) VALUES (?, ?, ?, ?, ?, ?)",
                  (str(guild_id), url, audio_url, title, duration, position))
        conn.commit()
        logging.info(f"Added song to queue for guild {guild_id}, position {position}")
    except Exception as e:
        logging.error(f"Error adding to queue for guild {guild_id}: {str(e)}")
    finally:
        conn.close()

def get_queue(guild_id):
    """Lấy hàng đợi theo guild_id."""
    try:
        conn = sqlite3.connect(r'.\data\queues.db')
        c = conn.cursor()
        c.execute("SELECT url, audio_url, title, duration FROM queues WHERE guild_id = ? ORDER BY position", (str(guild_id),))
        queue = [(row[0], row[1], row[2], row[3] or 0) for row in c.fetchall()]
        logging.info(f"Retrieved queue with {len(queue)} items for guild {guild_id}")
        return queue
    except Exception as e:
        logging.error(f"Error retrieving queue for guild {guild_id}: {str(e)}")
        return []
    finally:
        conn.close()

def remove_from_queue(guild_id, position):
    """Xóa bài hát khỏi hàng đợi theo vị trí."""
    try:
        conn = sqlite3.connect(r'.\data\queues.db')
        c = conn.cursor()
        c.execute("DELETE FROM queues WHERE guild_id = ? AND position = ?", (str(guild_id), position))
        c.execute("UPDATE queues SET position = position - 1 WHERE guild_id = ? AND position > ?", (str(guild_id), position))
        conn.commit()
        logging.info(f"Removed song from queue for guild {guild_id}, position {position}")
    except Exception as e:
        logging.error(f"Error removing from queue for guild {guild_id}: {str(e)}")
    finally:
        conn.close()

def clear_queue(guild_id):
    """Xóa toàn bộ hàng đợi của guild_id."""
    try:
        conn = sqlite3.connect(r'.\data\queues.db')
        c = conn.cursor()
        c.execute("DELETE FROM queues WHERE guild_id = ?", (str(guild_id),))
        conn.commit()
        logging.info(f"Cleared queue for guild {guild_id}")
    except Exception as e:
        logging.error(f"Error clearing queue for guild {guild_id}: {str(e)}")
    finally:
        conn.close()