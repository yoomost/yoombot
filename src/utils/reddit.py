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
from database import get_db_connection, add_reddit_post, is_reddit_post_sent

class RedditCog(commands.Cog):
    """Cog quản lý chức năng lấy và đăng ảnh từ r/hentai trên Reddit."""
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

    async def fetch_and_post_reddit_images(self):
        """Lấy và đăng ảnh từ r/hentai theo độ ưu tiên."""
        logging.info("Bắt đầu lấy ảnh từ r/hentai")

        # Kiểm tra kênh ảnh
        image_channel = self.bot.get_channel(int(IMAGE_CHANNEL_ID))
        if not image_channel:
            logging.error(f"Kênh ảnh {IMAGE_CHANNEL_ID} không tồn tại.")
            return False

        # Khởi tạo Reddit API
        reddit = await self.initialize_reddit()
        if not reddit:
            return False

        # Kiểm tra/tạo bảng reddit_priorities
        try:
            conn = get_db_connection("reddit.db")
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reddit_priorities (
                    type TEXT,  -- 'user' hoặc 'flair'
                    value TEXT, -- user_id hoặc flair
                    PRIMARY KEY (type, value)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reddit_posts (
                    post_id TEXT PRIMARY KEY,
                    title TEXT,
                    posted_at DATETIME
                )
            """)
            conn.commit()
            logging.debug("Đã kiểm tra/tạo bảng reddit_priorities và reddit_posts")
        except Exception as e:
            logging.error(f"Lỗi khi tạo bảng: {str(e)}", exc_info=True)
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            return False

        # Lấy danh sách user và flair ưu tiên
        try:
            cursor.execute("SELECT value FROM reddit_priorities WHERE type = 'user'")
            priority_users = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT value FROM reddit_priorities WHERE type = 'flair'")
            priority_flairs = [row[0] for row in cursor.fetchall()]
            logging.debug(f"User ưu tiên: {priority_users}, Flair ưu tiên: {priority_flairs}")
        except Exception as e:
            logging.error(f"Lỗi khi lấy user/flair ưu tiên: {str(e)}", exc_info=True)
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            return False

        # Lấy bài viết mới từ API Reddit
        posts = []
        try:
            subreddit = await reddit.subreddit("hentai")
            async for submission in subreddit.new(limit=50):  # Lấy 50 bài mới nhất
                if hasattr(submission, 'url') and submission.url.endswith(('.jpg', '.png', '.jpeg')):
                    if not is_reddit_post_sent(submission.id):
                        posts.append(submission)
            logging.info(f"Đã nhận được {len(posts)} bài viết hình ảnh mới từ r/hentai")
        except Exception as e:
            logging.error(f"Lỗi khi lấy bài viết từ Reddit: {str(e)}", exc_info=True)
            await reddit.close()
            return False

        if not posts:
            logging.warning("Không tìm thấy bài viết hình ảnh mới từ r/hentai.")
            await reddit.close()
            return False

        # Sắp xếp bài viết theo độ ưu tiên: user -> flair -> còn lại
        user_posts = []
        flair_posts = []
        other_posts = []
        for post in posts:
            author = post.author.name if post.author else None
            flair = post.link_flair_text
            if author and author in priority_users:
                user_posts.append(post)
            elif flair and flair in priority_flairs:
                flair_posts.append(post)
            else:
                other_posts.append(post)

        prioritized_posts = user_posts[:10]
        if len(prioritized_posts) < 10:
            prioritized_posts.extend(flair_posts[:10 - len(prioritized_posts)])
        if len(prioritized_posts) < 10:
            prioritized_posts.extend(other_posts[:10 - len(prioritized_posts)])

        sent_count = 0
        headers = {
            'User-Agent': REDDIT_USER_AGENT
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            for idx, post in enumerate(prioritized_posts[:10]):
                try:
                    img_url = post.url
                    logging.debug(f"Xử lý bài viết: {post.title}, URL: {img_url}")
                    embed = discord.Embed(
                        title=f"Ảnh từ r/hentai: {post.title}"[:256],
                        url=f"https://reddit.com{post.permalink}",
                        color=0xFF4500
                    )
                    embed.set_image(url=img_url)
                    embed.add_field(name="Tác giả", value=post.author.name if post.author else "Unknown", inline=True)
                    embed.add_field(name="Flair", value=post.link_flair_text or "None", inline=True)
                    embed.set_footer(text=f"Đăng lúc: {datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%H:%M %d/%m/%Y')}")

                    # Tải và gửi ảnh dưới dạng file
                    async with session.get(img_url) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            file = discord.File(fp=io.BytesIO(data), filename=f"image_{idx}.jpg")
                            await image_channel.send(embed=embed, file=file)
                            logging.info(f"Đã gửi embed với file ảnh cho {post.title}")
                            add_reddit_post(post.id, post.title)  # Lưu bài viết đã đăng
                            sent_count += 1
                        else:
                            logging.error(f"Không tải được ảnh từ {img_url}, mã lỗi: {resp.status}")
                            continue
                    await asyncio.sleep(1)
                except Exception as e:
                    logging.error(f"Lỗi khi xử lý bài viết {post.title}: {str(e)}", exc_info=True)
                    continue

        # Xóa các bài viết cũ hơn 24 giờ
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
            logging.debug("Đã đóng kết nối cơ sở dữ liệu")

        await reddit.close()
        logging.info(f"Hoàn tất xử lý và gửi {sent_count} ảnh")
        return sent_count

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

    @commands.command(name="post_reddit_images_now")
    @commands.has_role(ADMIN_ROLE_ID)
    async def post_reddit_images_now(self, ctx):
        """Đăng ảnh từ r/hentai ngay lập tức."""
        logging.info(f"Lệnh post_reddit_images_now được gọi bởi {ctx.author.id}")
        await ctx.send("Đang đăng ảnh ngay từ r/hentai...")
        try:
            sent_count = await self.fetch_and_post_reddit_images()
            logging.info(f"Lệnh post_reddit_images_now hoàn tất, đã gửi {sent_count} ảnh")
            await ctx.send(f"Đã đăng {sent_count} ảnh từ r/hentai.")
        except Exception as e:
            logging.error(f"Lỗi khi thực hiện post_reddit_images_now: {str(e)}", exc_info=True)
            await ctx.send(f"Lỗi khi đăng ảnh: {str(e)}")

    async def reddit_images_task(self):
        """Tác vụ nền kiểm tra ảnh từ r/hentai mỗi 15 phút."""
        logging.info("Khởi động tác vụ lấy ảnh từ r/hentai")
        while True:
            try:
                success = await self.fetch_and_post_reddit_images()
                if not success:
                    logging.warning("Chu kỳ lấy ảnh từ r/hentai không thành công, thử lại sau 60 giây")
                    await asyncio.sleep(60)
                    continue
            except Exception as e:
                logging.error(f"Lỗi trong reddit_images_task: {str(e)}", exc_info=True)
                await asyncio.sleep(60)
                continue
            logging.info("Hoàn thành chu kỳ lấy ảnh từ r/hentai, chờ 15 phút")
            await asyncio.sleep(910)

async def setup(bot):
    """Thiết lập Cog cho bot."""
    await bot.add_cog(RedditCog(bot))