import feedparser
import discord
import logging
import asyncio
import re
from datetime import datetime, timedelta
import pytz
import aiohttp
from config import NEWS_CHANNEL_ID
from database import add_news_article, get_db_connection

async def fetch_and_post_news(bot):
    """Lấy tin mới từ VnExpress và gửi đến kênh thông báo."""
    logging.info("Bắt đầu lấy tin mới từ VnExpress")
    
    # Kiểm tra kênh thông báo
    channel = bot.get_channel(NEWS_CHANNEL_ID)
    if not channel:
        logging.error(f"Kênh thông báo {NEWS_CHANNEL_ID} không tồn tại.")
        return False

    # Tải RSS feed với thử lại
    rss_url = "https://vnexpress.net/rss/tin-moi-nhat.rss"
    max_retries = 3
    rss_content = None
    for attempt in range(max_retries):
        try:
            logging.debug(f"Thử tải RSS feed, lần {attempt + 1}/{max_retries}")
            async with aiohttp.ClientSession() as session:
                async with session.get(rss_url, timeout=10) as resp:
                    if resp.status != 200:
                        logging.error(f"Không tải được RSS feed, mã lỗi: {resp.status}")
                        if attempt == max_retries - 1:
                            return False
                        await asyncio.sleep(5)
                        continue
                    rss_content = await resp.text()
                    break
        except Exception as e:
            logging.error(f"Lỗi khi tải RSS feed: {str(e)}", exc_info=True)
            if attempt == max_retries - 1:
                return False
            await asyncio.sleep(5)
            continue
    else:
        logging.error("Hết số lần thử tải RSS feed.")
        return False

    # Phân tích RSS feed
    logging.debug("Bắt đầu phân tích RSS feed")
    try:
        feed = feedparser.parse(rss_content)
        logging.info(f"Tìm thấy {len(feed.entries)} bài báo trong RSS feed")
    except Exception as e:
        logging.error(f"Lỗi khi phân tích RSS feed: {str(e)}", exc_info=True)
        return False
    
    if not feed.entries:
        logging.warning("Không tìm thấy bài báo nào trong RSS feed của VnExpress.")
        return False

    # Kiểm tra/tạo bảng news và sửa đổi cấu trúc nếu cần
    try:
        conn = get_db_connection("news.db")
        cursor = conn.cursor()
        # Kiểm tra cấu trúc bảng
        cursor.execute("PRAGMA table_info(news)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'article_id' not in columns or 'title' not in columns or 'published' not in columns:
            logging.warning("Cấu trúc bảng news không đúng, tạo lại bảng")
            cursor.execute("DROP TABLE IF EXISTS news")
            cursor.execute("""
                CREATE TABLE news (
                    article_id TEXT PRIMARY KEY,
                    title TEXT,
                    published TEXT
                )
            """)
            conn.commit()
            logging.debug("Đã tạo lại bảng news với cấu trúc đúng")
        else:
            logging.debug("Cấu trúc bảng news đã đúng")
        
        # Xóa bài cũ hơn 24 giờ
        cutoff_time = (datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")) - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM news WHERE published < ?", (cutoff_time,))
        conn.commit()
        logging.debug(f"Đã kiểm tra/tạo bảng news và xóa {cursor.rowcount} bài cũ")
    except Exception as e:
        logging.error(f"Lỗi khi tạo bảng news hoặc xóa bài cũ: {str(e)}", exc_info=True)
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        return False

    sent_count = 0
    new_articles = 0
    vn_timezone = pytz.timezone("Asia/Ho_Chi_Minh")
    try:
        for entry in reversed(feed.entries[:5]):
            try:
                article_id = entry.get("id", entry.get("link", ""))
                if not article_id:
                    logging.warning(f"Bài báo không có ID hoặc link: {entry.get('title', 'Không có tiêu đề')}")
                    continue

                title = entry.get("title", "Không có tiêu đề")
                description = entry.get("description", "Không có mô tả")
                link = entry.get("link", "")

                clean_description = re.sub(r"<[^>]+>", "", description).strip()
                if not clean_description and description:
                    clean_description = description.split(">")[1].strip() if ">" in description else "Không có mô tả"

                pub_date_str = entry.get("pubDate", None)
                if pub_date_str:
                    try:
                        pub_date_utc = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
                        pub_date_vn = pub_date_utc.astimezone(vn_timezone)
                        published = pub_date_vn.strftime("%H:%M %d/%m/%Y")
                    except (ValueError, TypeError):
                        logging.warning(f"Không thể phân tích pubDate: {pub_date_str}, sử dụng giờ hiện tại")
                        published = datetime.now(vn_timezone).strftime("%H:%M %d/%m/%Y")
                else:
                    logging.warning("Không có pubDate, sử dụng giờ hiện tại")
                    published = datetime.now(vn_timezone).strftime("%H:%M %d/%m/%Y")

                thumbnail_url = ""
                if description and "src=" in description:
                    try:
                        start = description.index("src=\"") + 5
                        end = description.index("\"", start)
                        thumbnail_url = description[start:end]
                    except ValueError:
                        logging.debug("Không tìm thấy URL hình ảnh trong mô tả")

                embed = discord.Embed(
                    title=title[:256],
                    url=link,
                    description=clean_description[:512],
                    color=0xF28C38
                )
                embed.add_field(name="Nguồn", value="VnExpress", inline=True)
                embed.set_author(name="VnExpress", icon_url="https://s1.vnecdn.net/vnexpress/restruct/i/v92/logos/32x32.png")
                embed.set_footer(text=f"Đăng lúc: {published}", icon_url="https://s1.vnecdn.net/vnexpress/restruct/i/v92/logos/120x120.png")
                if thumbnail_url:
                    embed.set_thumbnail(url=thumbnail_url)

                # Gửi embed và lưu vào CSDL sau khi gửi thành công
                await channel.send(embed=embed)
                add_news_article(article_id, title, published)
                logging.info(f"Đã gửi tin: {title}")
                sent_count += 1
                new_articles += 1
                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Lỗi khi xử lý bài báo {title}: {str(e)}", exc_info=True)
                continue

        if new_articles == 0:
            logging.info("Không tìm thấy bài báo mới nào để đăng.")
        logging.info(f"Hoàn tất xử lý và gửi {sent_count} tin")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi xử lý RSS feed: {str(e)}", exc_info=True)
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            logging.debug("Đã đóng kết nối cơ sở dữ liệu")

async def news_task(bot):
    """Tác vụ nền kiểm tra tin mới mỗi 15 phút."""
    logging.info("Khởi động tác vụ tin tức nền")
    while True:
        try:
            success = await fetch_and_post_news(bot)
            if not success:
                logging.warning("Chu kỳ lấy tin không thành công, thử lại sau 60 giây")
                await asyncio.sleep(60)
                continue
        except Exception as e:
            logging.error(f"Lỗi trong news_task: {str(e)}", exc_info=True)
            await asyncio.sleep(60)
            continue
        logging.info("Hoàn thành chu kỳ lấy tin, chờ 15 phút")
        await asyncio.sleep(910)

async def setup(bot):
    """Thiết lập tác vụ tin tức."""
    bot.loop.create_task(news_task(bot))