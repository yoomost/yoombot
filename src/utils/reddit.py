import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime
import pytz
import asyncpraw
import aiohttp
import io
from config import IMAGE_CHANNEL_ID, ADMIN_ROLE_ID, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from database import get_db_connection, add_reddit_post, is_reddit_post_sent, migrate_reddit_db

class RedditCog(commands.Cog):
    """Cog quản lý chức năng lấy và đăng ảnh từ các subreddit trên Reddit."""
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.reddit_images_task())

    async def initialize_reddit(self):
        """Khởi tạo kết nối với Reddit API."""
        try:
            reddit = asyncpraw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent=REDDIT_USER_AGENT
            )
            logging.info("Đã khởi tạo kết nối với Reddit API")
            return reddit
        except Exception as e:
            logging.error(f"Lỗi khi khởi tạo Reddit API: {str(e)}", exc_info=True)
            return None

    async def fetch_from_subreddit(self, subreddit_name, reddit, image_channel, cursor, priority_users, priority_flairs, session):
        """Lấy và đăng ảnh từ một subreddit cụ thể."""
        posts = []
        try:
            subreddit = await reddit.subreddit(subreddit_name)
            async for submission in subreddit.new(limit=50):  # Lấy 50 bài mới nhất
                if hasattr(submission, 'url') and submission.url.endswith(('.jpg', '.png', '.jpeg')):
                    if not is_reddit_post_sent(submission.id, subreddit_name):
                        posts.append(submission)
            logging.info(f"Đã nhận được {len(posts)} bài viết hình ảnh mới từ r/{subreddit_name}")
        except asyncpraw.exceptions.RedditAPIException as e:
            if "RATELIMIT" in str(e):
                reset_time = int(e.response.headers.get("X-Ratelimit-Reset", 60))
                logging.warning(f"Rate limit reached for r/{subreddit_name}, waiting {reset_time} seconds")
                await asyncio.sleep(reset_time)
                return 0
            logging.error(f"Lỗi khi lấy bài viết từ r/{subreddit_name}: {str(e)}", exc_info=True)
            return 0
        except Exception as e:
            logging.error(f"Lỗi khi lấy bài viết từ r/{subreddit_name}: {str(e)}", exc_info=True)
            return 0

        # Sắp xếp bài viết theo độ ưu tiên: user -> flair -> còn lại
        user_posts = [p for p in posts if p.author and p.author.name in priority_users]
        flair_posts = [p for p in posts if p.link_flair_text in priority_flairs]
        other_posts = [p for p in posts if p not in user_posts and p not in flair_posts]

        prioritized_posts = user_posts[:5]
        if len(prioritized_posts) < 5:
            prioritized_posts.extend(flair_posts[:5 - len(prioritized_posts)])
        if len(prioritized_posts) < 5:
            prioritized_posts.extend(other_posts[:5 - len(prioritized_posts)])

        sent_count = 0
        max_file_size = 8 * 1024 * 1024  # 8MB limit for free Discord bots
        for idx, post in enumerate(prioritized_posts):
            try:
                img_url = post.url
                logging.debug(f"Xử lý bài viết từ r/{subreddit_name}: {post.title}, URL: {img_url}")
                async with session.get(img_url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        if len(data) > max_file_size:
                            logging.warning(f"Skipped image from r/{subreddit_name} (post {post.id}): File size {len(data)} bytes exceeds 8MB limit")
                            continue
                        file = discord.File(fp=io.BytesIO(data), filename=f"image_{idx}.jpg")
                        embed = discord.Embed(
                            title=f"Ảnh từ r/{subreddit_name}: {post.title}"[:256],
                            url=f"https://reddit.com{post.permalink}",
                            color=0xFF4500
                        )
                        embed.set_image(url=img_url)
                        embed.add_field(name="Tác giả", value=post.author.name if post.author else "Unknown", inline=True)
                        embed.add_field(name="Flair", value=post.link_flair_text or "None", inline=True)
                        embed.set_footer(text=f"Đăng lúc: {datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%H:%M %d/%m/%Y')}")

                        await image_channel.send(embed=embed, file=file)
                        add_reddit_post(post.id, post.title, subreddit_name)
                        sent_count += 1
                    else:
                        logging.error(f"Không tải được ảnh từ {img_url}, mã lỗi: {resp.status}")
                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Lỗi khi xử lý bài viết từ r/{subreddit_name}: {str(e)}", exc_info=True)
        return sent_count

    async def fetch_and_post_reddit_images(self):
        """Lấy và đăng ảnh từ danh sách subreddit."""
        logging.info("Bắt đầu lấy ảnh từ các subreddit")

        image_channel = self.bot.get_channel(int(IMAGE_CHANNEL_ID))
        if not image_channel:
            logging.error(f"Kênh ảnh {IMAGE_CHANNEL_ID} không tồn tại.")
            return False

        reddit = await self.initialize_reddit()
        if not reddit:
            return False

        try:
            conn = get_db_connection("reddit.db")
            cursor = conn.cursor()
            # Migrate database to ensure correct schema
            migrate_reddit_db()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reddit_priorities (
                    type TEXT, value TEXT, PRIMARY KEY (type, value)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reddit_posts (
                    post_id TEXT, subreddit TEXT, title TEXT, posted_at DATETIME,
                    PRIMARY KEY (post_id, subreddit)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reddit_subreddits (
                    subreddit_name TEXT PRIMARY KEY
                )
            """)
            conn.commit()
            logging.debug("Đã kiểm tra/tạo bảng reddit_priorities, reddit_posts, và reddit_subreddits")

            # Lấy danh sách subreddit
            cursor.execute("SELECT subreddit_name FROM reddit_subreddits")
            subreddits = [row[0] for row in cursor.fetchall()]
            if not subreddits:
                subreddits = ['hentai']  # Mặc định nếu danh sách trống
                cursor.execute("INSERT OR IGNORE INTO reddit_subreddits (subreddit_name) VALUES (?)", ('hentai',))
                conn.commit()

            # Lấy danh sách user và flair ưu tiên
            cursor.execute("SELECT value FROM reddit_priorities WHERE type = 'user'")
            priority_users = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT value FROM reddit_priorities WHERE type = 'flair'")
            priority_flairs = [row[0] for row in cursor.fetchall()]
            logging.debug(f"Subreddits: {subreddits}, User ưu tiên: {priority_users}, Flair ưu tiên: {priority_flairs}")
        except Exception as e:
            logging.error(f"Lỗi khi khởi tạo cơ sở dữ liệu: {str(e)}", exc_info=True)
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            return False

        headers = {'User-Agent': REDDIT_USER_AGENT}
        total_sent = 0
        async with aiohttp.ClientSession(headers=headers) as session:
            for subreddit_name in subreddits:
                sent = await self.fetch_from_subreddit(subreddit_name, reddit, image_channel, cursor, priority_users, priority_flairs, session)
                total_sent += sent
                await asyncio.sleep(2)  # Chờ để tránh vượt giới hạn API

        try:
            cursor.execute("DELETE FROM reddit_posts WHERE posted_at < datetime('now', '-24 hours')")
            conn.commit()
            logging.debug("Đã xóa các bài viết Reddit cũ hơn 24 giờ")
        except Exception as e:
            logging.error(f"Lỗi khi xóa bài viết cũ: {str(e)}", exc_info=True)

        if cursor:
            cursor.close()
        if conn:
            conn.close()
        await reddit.close()
        logging.info(f"Hoàn tất xử lý và gửi {total_sent} ảnh")
        return total_sent > 0

    @commands.command(name="add_reddit_user")
    @commands.has_role(ADMIN_ROLE_ID)
    async def add_reddit_user(self, ctx, username: str):
        """Thêm user Reddit vào danh sách ưu tiên."""
        try:
            conn = get_db_connection("reddit.db")
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO reddit_priorities (type, value) VALUES (?, ?)", ('user', username))
            conn.commit()
            logging.info(f"Đã thêm user Reddit {username} vào reddit_priorities bởi {ctx.author.id}")
            await ctx.send(f"Đã thêm user Reddit {username} vào danh sách ưu tiên.")
        except Exception as e:
            logging.error(f"Lỗi khi thêm user Reddit {username}: {str(e)}", exc_info=True)
            await ctx.send(f"Lỗi khi thêm user Reddit {username}: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @commands.command(name="remove_reddit_user")
    @commands.has_role(ADMIN_ROLE_ID)
    async def remove_reddit_user(self, ctx, username: str):
        """Xóa user Reddit khỏi danh sách ưu tiên."""
        try:
            conn = get_db_connection("reddit.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reddit_priorities WHERE type = 'user' AND value = ?", (username,))
            if cursor.rowcount > 0:
                conn.commit()
                logging.info(f"Đã xóa user Reddit {username} khỏi reddit_priorities bởi {ctx.author.id}")
                await ctx.send(f"Đã xóa user Reddit {username} khỏi danh sách ưu tiên.")
            else:
                logging.info(f"Không tìm thấy user Reddit {username} trong reddit_priorities")
                await ctx.send(f"Không tìm thấy user Reddit {username} trong danh sách ưu tiên.")
        except Exception as e:
            logging.error(f"Lỗi khi xóa user Reddit {username}: {str(e)}", exc_info=True)
            await ctx.send(f"Lỗi khi xóa user Reddit {username}: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @commands.command(name="add_reddit_flair")
    @commands.has_role(ADMIN_ROLE_ID)
    async def add_reddit_flair(self, ctx, flair: str):
        """Thêm flair Reddit vào danh sách ưu tiên."""
        try:
            conn = get_db_connection("reddit.db")
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO reddit_priorities (type, value) VALUES (?, ?)", ('flair', flair))
            conn.commit()
            logging.info(f"Đã thêm flair Reddit {flair} vào reddit_priorities bởi {ctx.author.id}")
            await ctx.send(f"Đã thêm flair Reddit {flair} vào danh sách ưu tiên.")
        except Exception as e:
            logging.error(f"Lỗi khi thêm flair Reddit {flair}: {str(e)}", exc_info=True)
            await ctx.send(f"Lỗi khi thêm flair Reddit {flair}: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @commands.command(name="remove_reddit_flair")
    @commands.has_role(ADMIN_ROLE_ID)
    async def remove_reddit_flair(self, ctx, flair: str):
        """Xóa flair Reddit khỏi danh sách ưu tiên."""
        try:
            conn = get_db_connection("reddit.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reddit_priorities WHERE type = 'flair' AND value = ?", (flair,))
            if cursor.rowcount > 0:
                conn.commit()
                logging.info(f"Đã xóa flair Reddit {flair} khỏi reddit_priorities bởi {ctx.author.id}")
                await ctx.send(f"Đã xóa flair Reddit {flair} khỏi danh sách ưu tiên.")
            else:
                logging.info(f"Không tìm thấy flair Reddit {flair} trong reddit_priorities")
                await ctx.send(f"Không tìm thấy flair Reddit {flair} trong danh sách ưu tiên.")
        except Exception as e:
            logging.error(f"Lỗi khi xóa flair Reddit {flair}: {str(e)}", exc_info=True)
            await ctx.send(f"Lỗi khi xóa flair Reddit {flair}: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @commands.command(name="add_subreddit")
    @commands.has_role(ADMIN_ROLE_ID)
    async def add_subreddit(self, ctx, subreddit_name: str):
        """Thêm subreddit vào danh sách theo dõi."""
        try:
            conn = get_db_connection("reddit.db")
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO reddit_subreddits (subreddit_name) VALUES (?)", (subreddit_name,))
            conn.commit()
            logging.info(f"Đã thêm subreddit r/{subreddit_name} bởi {ctx.author.id}")
            await ctx.send(f"Đã thêm subreddit r/{subreddit_name} vào danh sách theo dõi.")
        except Exception as e:
            logging.error(f"Lỗi khi thêm subreddit r/{subreddit_name}: {str(e)}", exc_info=True)
            await ctx.send(f"Lỗi khi thêm subreddit r/{subreddit_name}: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @commands.command(name="remove_subreddit")
    @commands.has_role(ADMIN_ROLE_ID)
    async def remove_subreddit(self, ctx, subreddit_name: str):
        """Xóa subreddit khỏi danh sách theo dõi."""
        try:
            conn = get_db_connection("reddit.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reddit_subreddits WHERE subreddit_name = ?", (subreddit_name,))
            if cursor.rowcount > 0:
                conn.commit()
                logging.info(f"Đã xóa subreddit r/{subreddit_name} bởi {ctx.author.id}")
                await ctx.send(f"Đã xóa subreddit r/{subreddit_name} khỏi danh sách theo dõi.")
            else:
                logging.info(f"Không tìm thấy subreddit r/{subreddit_name}")
                await ctx.send(f"Không tìm thấy subreddit r/{subreddit_name} trong danh sách.")
        except Exception as e:
            logging.error(f"Lỗi khi xóa subreddit r/{subreddit_name}: {str(e)}", exc_info=True)
            await ctx.send(f"Lỗi khi xóa subreddit r/{subreddit_name}: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @commands.command(name="post_reddit_images_now")
    @commands.has_role(ADMIN_ROLE_ID)
    async def post_reddit_images_now(self, ctx):
        """Đăng ảnh từ các subreddit ngay lập tức."""
        logging.info(f"Lệnh post_reddit_images_now được gọi bởi {ctx.author.id}")
        await ctx.send("Đang đăng ảnh từ các subreddit...")
        try:
            success = await self.fetch_and_post_reddit_images()
            await ctx.send(f"Đã đăng ảnh từ các subreddit {'thành công' if success else 'thất bại'}.")
        except Exception as e:
            logging.error(f"Lỗi khi thực hiện post_reddit_images_now: {str(e)}", exc_info=True)
            await ctx.send(f"Lỗi khi đăng ảnh: {str(e)}")

    async def reddit_images_task(self):
        """Tác vụ nền kiểm tra ảnh từ các subreddit mỗi 15 phút."""
        logging.info("Khởi động tác vụ lấy ảnh từ các subreddit")
        while True:
            try:
                success = await self.fetch_and_post_reddit_images()
                if not success:
                    logging.warning("Chu kỳ lấy ảnh từ các subreddit không thành công, thử lại sau 60 giây")
                    await asyncio.sleep(60)
                    continue
            except Exception as e:
                logging.error(f"Lỗi trong reddit_images_task: {str(e)}", exc_info=True)
                await asyncio.sleep(60)
                continue
            logging.info("Hoàn thành chu kỳ lấy ảnh từ các subreddit, chờ 15 phút")
            await asyncio.sleep(910)

async def setup(bot):
    """Thiết lập Cog cho bot."""
    await bot.add_cog(RedditCog(bot))