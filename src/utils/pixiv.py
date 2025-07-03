import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime
import pytz
from pixivpy_async import AppPixivAPI
import aiohttp
import io
from config import IMAGE_CHANNEL_ID, PIXIV_REFRESH_TOKEN, ADMIN_ROLE_ID
from database import get_db_connection

class PixivCog(commands.Cog):
    """Cog quản lý chức năng lấy và đăng ảnh từ Pixiv."""
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.x_images_task())

    async def refresh_access_token(self, api):
        """Làm mới access token cho Pixiv API."""
        try:
            await api.login(refresh_token=PIXIV_REFRESH_TOKEN)
            logging.info("Sử dụng refresh token để đăng nhập Pixiv")
            if api.refresh_token and api.refresh_token != PIXIV_REFRESH_TOKEN:
                with open("config.py", "a") as f:
                    f.write(f"\nPIXIV_REFRESH_TOKEN = \"{api.refresh_token}\"\n")
                logging.info("Đã lưu refresh token mới vào config.py")
            return True
        except Exception as e:
            logging.warning(f"Refresh token không hợp lệ, thử lại với login_web: {str(e)}")
            try:
                await api.login_web()
                logging.info("Đăng nhập Pixiv thành công qua web")
                if api.refresh_token:
                    with open("config.py", "a") as f:
                        f.write(f"\nPIXIV_REFRESH_TOKEN = \"{api.refresh_token}\"\n")
                    logging.info("Đã lưu refresh token vào config.py")
                return True
            except Exception as e:
                logging.error(f"Lỗi khi đăng nhập Pixiv: {str(e)}", exc_info=True)
                return False

    async def fetch_and_post_x_images(self):
        """Lấy và đăng ảnh từ Pixiv theo độ ưu tiên."""
        logging.info("Bắt đầu lấy ảnh từ Pixiv")
        
        # Kiểm tra kênh ảnh
        image_channel = self.bot.get_channel(int(IMAGE_CHANNEL_ID))
        if not image_channel:
            logging.error(f"Kênh ảnh {IMAGE_CHANNEL_ID} không tồn tại.")
            return False

        # Khởi tạo API Pixiv
        api = AppPixivAPI()
        if not await self.refresh_access_token(api):
            return False

        # Kiểm tra/tạo bảng pixiv_priorities
        try:
            conn = get_db_connection("pixiv.db")
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pixiv_priorities (
                    type TEXT,  -- 'artist' hoặc 'tag'
                    value TEXT, -- artist_id hoặc tag
                    PRIMARY KEY (type, value)
                )
            """)
            conn.commit()
            logging.debug("Đã kiểm tra/tạo bảng pixiv_priorities")
        except Exception as e:
            logging.error(f"Lỗi khi tạo bảng pixiv_priorities: {str(e)}", exc_info=True)
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            return False

        # Lấy danh sách artist và tag ưu tiên
        try:
            cursor.execute("SELECT value FROM pixiv_priorities WHERE type = 'artist'")
            priority_artists = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT value FROM pixiv_priorities WHERE type = 'tag'")
            priority_tags = [row[0] for row in cursor.fetchall()]
            logging.debug(f"Artist ưu tiên: {priority_artists}, Tag ưu tiên: {priority_tags}")
        except Exception as e:
            logging.error(f"Lỗi khi lấy artist/tag ưu tiên: {str(e)}", exc_info=True)
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            return False

        # Lấy ảnh từ API Pixiv
        illustrations = []
        try:
            logging.info("Gọi API illust_recommended...")
            json_result = await api.illust_recommended()
            illustrations = json_result.illusts
            logging.info(f"Đã nhận được {len(illustrations)} tác phẩm từ Pixiv")
        except Exception as e:
            logging.error(f"Lỗi khi lấy ảnh từ Pixiv: {str(e)}", exc_info=True)
            return False

        if not illustrations:
            logging.warning("Không tìm thấy ảnh nào từ Pixiv.")
            return False

        # Sắp xếp ảnh theo độ ưu tiên: artist -> tag -> còn lại
        artist_images = []
        tag_images = []
        other_images = []
        for illust in illustrations:
            artist_id = str(illust.user.id)
            tags = [tag.name for tag in illust.tags]
            if artist_id in priority_artists:
                artist_images.append(illust)
            elif any(tag in priority_tags for tag in tags):
                tag_images.append(illust)
            else:
                other_images.append(illust)

        prioritized_images = artist_images[:10]
        if len(prioritized_images) < 10:
            prioritized_images.extend(tag_images[:10 - len(prioritized_images)])
        if len(prioritized_images) < 10:
            prioritized_images.extend(other_images[:10 - len(prioritized_images)])

        sent_count = 0
        headers = {
            'Referer': 'https://www.pixiv.net/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/*'
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            for idx, illust in enumerate(prioritized_images[:10]):
                try:
                    # Log chi tiết cấu trúc dữ liệu
                    logging.debug(f"Chi tiết tác phẩm {illust.title}: keys={illust.keys()}")
                    
                    # Trích xuất URL ảnh
                    img_url = None
                    if 'image_urls' in illust:
                        img_url = illust.image_urls.get('medium') or \
                                  illust.image_urls.get('square_medium') or \
                                  illust.image_urls.get('large')
                    elif 'meta_pages' in illust and illust.meta_pages and illust.meta_pages[0].image_urls:
                        img_url = illust.meta_pages[0].image_urls.get('medium') or \
                                  illust.meta_pages[0].image_urls.get('square_medium') or \
                                  illust.meta_pages[0].image_urls.get('large')
                    elif 'meta_single_page' in illust and illust.meta_single_page.get("original_image_url"):
                        img_url = illust.meta_single_page["original_image_url"]

                    if not img_url:
                        logging.warning(f"Bỏ qua tác phẩm {illust.title}: Không tìm thấy URL ảnh")
                        continue

                    logging.debug(f"Xử lý ảnh: {illust.title}, URL: {img_url}")
                    embed = discord.Embed(
                        title=f"Ảnh từ Pixiv: {illust.title}"[:256],
                        url=f"https://www.pixiv.net/artworks/{illust.id}",
                        color=0x1DA1F2
                    )
                    embed.set_image(url=img_url)
                    embed.add_field(name="Tác giả", value=illust.user.name, inline=True)
                    embed.add_field(name="Thẻ", value=", ".join(tag.name for tag in illust.tags)[:100], inline=True)
                    embed.set_footer(text=f"Đăng lúc: {datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%H:%M %d/%m/%Y')}")

                    # Tải và gửi ảnh dưới dạng file
                    async with session.get(img_url) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            file = discord.File(fp=io.BytesIO(data), filename=f"image_{idx}.jpg")
                            await image_channel.send(embed=embed, file=file)
                            logging.info(f"Đã gửi embed với file ảnh cho {illust.title}")
                            sent_count += 1
                        else:
                            logging.error(f"Không tải được ảnh từ {img_url}, mã lỗi: {resp.status}")
                            continue
                    await asyncio.sleep(1)
                except Exception as e:
                    logging.error(f"Lỗi khi xử lý ảnh {illust.title}: {str(e)}", exc_info=True)
                    continue

        if cursor:
            cursor.close()
        if conn:
            conn.close()
            logging.debug("Đã đóng kết nối cơ sở dữ liệu")

        logging.info(f"Hoàn tất xử lý và gửi {sent_count} ảnh")
        return sent_count

    @commands.command(name="add_artist")
    @commands.has_role(ADMIN_ROLE_ID)
    async def add_artist(self, ctx, artist_id: str):
        """Thêm artist vào danh sách ưu tiên."""
        try:
            conn = get_db_connection("pixiv.db")
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO pixiv_priorities (type, value) VALUES (?, ?)", ('artist', artist_id))
            conn.commit()
            logging.info(f"Đã thêm artist {artist_id} vào pixiv_priorities bởi {ctx.author.id}")
            await ctx.send(f"Đã thêm artist {artist_id} vào danh sách ưu tiên.")
        except Exception as e:
            logging.error(f"Lỗi khi thêm artist {artist_id}: {str(e)}", exc_info=True)
            await ctx.send(f"Lỗi khi thêm artist {artist_id}: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @commands.command(name="remove_artist")
    @commands.has_role(ADMIN_ROLE_ID)
    async def remove_artist(self, ctx, artist_id: str):
        """Xóa artist khỏi danh sách ưu tiên."""
        try:
            conn = get_db_connection("pixiv.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pixiv_priorities WHERE type = 'artist' AND value = ?", (artist_id,))
            if cursor.rowcount > 0:
                conn.commit()
                logging.info(f"Đã xóa artist {artist_id} khỏi pixiv_priorities bởi {ctx.author.id}")
                await ctx.send(f"Đã xóa artist {artist_id} khỏi danh sách ưu tiên.")
            else:
                logging.info(f"Không tìm thấy artist {artist_id} trong pixiv_priorities")
                await ctx.send(f"Không tìm thấy artist {artist_id} trong danh sách ưu tiên.")
        except Exception as e:
            logging.error(f"Lỗi khi xóa artist {artist_id}: {str(e)}", exc_info=True)
            await ctx.send(f"Lỗi khi xóa artist {artist_id}: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @commands.command(name="add_tag")
    @commands.has_role(ADMIN_ROLE_ID)
    async def add_tag(self, ctx, tag: str):
        """Thêm tag vào danh sách ưu tiên."""
        try:
            conn = get_db_connection("pixiv.db")
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO pixiv_priorities (type, value) VALUES (?, ?)", ('tag', tag))
            conn.commit()
            logging.info(f"Đã thêm tag {tag} vào pixiv_priorities bởi {ctx.author.id}")
            await ctx.send(f"Đã thêm tag {tag} vào danh sách ưu tiên.")
        except Exception as e:
            logging.error(f"Lỗi khi thêm tag {tag}: {str(e)}", exc_info=True)
            await ctx.send(f"Lỗi khi thêm tag {tag}: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @commands.command(name="remove_tag")
    @commands.has_role(ADMIN_ROLE_ID)
    async def remove_tag(self, ctx, tag: str):
        """Xóa tag khỏi danh sách ưu tiên."""
        try:
            conn = get_db_connection("pixiv.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pixiv_priorities WHERE type = 'tag' AND value = ?", (tag,))
            if cursor.rowcount > 0:
                conn.commit()
                logging.info(f"Đã xóa tag {tag} khỏi pixiv_priorities bởi {ctx.author.id}")
                await ctx.send(f"Đã xóa tag {tag} khỏi danh sách ưu tiên.")
            else:
                logging.info(f"Không tìm thấy tag {tag} trong pixiv_priorities")
                await ctx.send(f"Không tìm thấy tag {tag} trong danh sách ưu tiên.")
        except Exception as e:
            logging.error(f"Lỗi khi xóa tag {tag}: {str(e)}", exc_info=True)
            await ctx.send(f"Lỗi khi xóa tag {tag}: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @commands.command(name="post_images_now")
    @commands.has_role(ADMIN_ROLE_ID)
    async def post_images_now(self, ctx):
        """Đăng ảnh từ Pixiv ngay lập tức."""
        logging.info(f"Lệnh post_images_now được gọi bởi {ctx.author.id}")
        await ctx.send("Đang đăng ảnh ngay...")
        try:
            sent_count = await self.fetch_and_post_x_images()
            logging.info(f"Lệnh post_images_now hoàn tất, đã gửi {sent_count} ảnh")
            await ctx.send(f"Đã đăng {sent_count} ảnh từ Pixiv.")
        except Exception as e:
            logging.error(f"Lỗi khi thực hiện post_images_now: {str(e)}", exc_info=True)
            await ctx.send(f"Lỗi khi đăng ảnh: {str(e)}")

    async def x_images_task(self):
        """Tác vụ nền kiểm tra ảnh từ Pixiv mỗi 15 phút."""
        logging.info("Khởi động tác vụ lấy ảnh từ Pixiv")
        while True:
            try:
                success = await self.fetch_and_post_x_images()
                if not success:
                    logging.warning("Chu kỳ lấy ảnh không thành công, thử lại sau 60 giây")
                    await asyncio.sleep(60)
                    continue
            except Exception as e:
                logging.error(f"Lỗi trong x_images_task: {str(e)}", exc_info=True)
                await asyncio.sleep(60)
                continue
            logging.info("Hoàn thành chu kỳ lấy ảnh từ Pixiv, chờ 15 phút")
            await asyncio.sleep(910)

async def setup(bot):
    """Thiết lập Cog cho bot."""
    await bot.add_cog(PixivCog(bot))