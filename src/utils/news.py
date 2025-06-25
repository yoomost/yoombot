import feedparser
import discord
import logging
import asyncio
import re
from datetime import datetime
import pytz
from config import NEWS_CHANNEL_ID
from database import add_news_article, is_article_sent

async def fetch_and_post_news(bot):
    """Lấy tin mới từ VnExpress và gửi đến kênh thông báo."""
    logging.info("Bắt đầu lấy tin mới từ VnExpress")
    rss_url = "https://vnexpress.net/rss/tin-moi-nhat.rss"
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            logging.warning("Không tìm thấy bài báo nào trong RSS feed của VnExpress.")
            return

        channel = bot.get_channel(NEWS_CHANNEL_ID)
        if not channel:
            logging.error(f"Kênh thông báo {NEWS_CHANNEL_ID} không tồn tại.")
            return

        logging.info(f"Tìm thấy {len(feed.entries)} bài báo trong RSS feed")
        vn_timezone = pytz.timezone("Asia/Ho_Chi_Minh")  # GMT+7
        for entry in reversed(feed.entries[:3]):  # Lấy 5 bài mới nhất
            article_id = entry.get("id", entry.link)
            if is_article_sent(article_id):
                logging.debug(f"Bài báo đã gửi trước đó: {article_id}")
                continue

            title = entry.get("title", "Không có tiêu đề")
            description = entry.get("description", "Không có mô tả")
            link = entry.get("link", "")

            # Clean HTML from description
            clean_description = re.sub(r"<[^>]+>", "", description).strip()
            if not clean_description and description:
                clean_description = description.split(">")[1].strip() if ">" in description else "Không có mô tả"

            # Parse and convert pubDate to GMT+7
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

            # Extract thumbnail from description (if available)
            thumbnail_url = ""
            if description and "src=" in description:
                try:
                    start = description.index("src=\"") + 5
                    end = description.index("\"", start)
                    thumbnail_url = description[start:end]
                except ValueError:
                    logging.debug("Không tìm thấy URL hình ảnh trong mô tả")

            # Tạo embed Discord
            embed = discord.Embed(
                title=title[:256],
                url=link,
                description=clean_description[:512],
                color=0xF28C38  # Màu cam của VnExpress
            )
            embed.add_field(name="Nguồn", value="VnExpress", inline=True)
            embed.set_author(name="VnExpress", icon_url="https://s1.vnecdn.net/vnexpress/restruct/i/v92/logos/32x32.png")
            embed.set_footer(text=f"Đăng lúc: {published}", icon_url="https://s1.vnecdn.net/vnexpress/restruct/i/v92/logos/120x120.png")
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)

            # Gửi embed
            await channel.send(embed=embed)
            add_news_article(article_id, title, published)
            logging.info(f"Đã gửi tin: {title}")

            # Đợi để tránh gửi quá nhanh
            await asyncio.sleep(1)

    except Exception as e:
        logging.error(f"Lỗi khi lấy/gửi tin mới từ VnExpress: {str(e)}")

async def news_task(bot):
    """Tác vụ nền kiểm tra tin mới mỗi 15 phút."""
    logging.info("Khởi động tác vụ tin tức nền")
    while True:
        await fetch_and_post_news(bot)
        logging.info("Hoàn thành chu kỳ lấy tin, chờ 15 phút")
        await asyncio.sleep(900)  # 15 phút