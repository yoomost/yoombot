import discord
import logging
import asyncio
from datetime import datetime
import pytz
from pixivpy_async import AppPixivAPI
import aiohttp
import io
from config import IMAGE_CHANNEL_ID, PIXIV_REFRESH_TOKEN
from database import get_db_connection

async def fetch_and_post_x_images(bot):
    """Lấy và đăng ảnh từ Pixiv."""
    logging.info("Bắt đầu lấy ảnh từ Pixiv")
    
    # Kiểm tra kênh ảnh
    image_channel = bot.get_channel(int(IMAGE_CHANNEL_ID))
    if not image_channel:
        logging.error(f"Kênh ảnh {IMAGE_CHANNEL_ID} không tồn tại.")
        return

    # Khởi tạo API Pixiv
    api = AppPixivAPI()
    try:
        if PIXIV_REFRESH_TOKEN:
            try:
                await api.login(refresh_token=PIXIV_REFRESH_TOKEN)
                logging.info("Sử dụng refresh token để đăng nhập Pixiv")
            except Exception as e:
                logging.warning(f"Refresh token không hợp lệ, thử lại với login_web: {str(e)}")
                await api.login_web()
                logging.info("Đăng nhập Pixiv thành công qua web")
                if api.refresh_token:
                    with open("config.py", "a") as f:
                        f.write(f"\nPIXIV_REFRESH_TOKEN = \"{api.refresh_token}\"\n")
                    logging.info("Đã lưu refresh token vào config.py")
        else:
            await api.login_web()
            logging.info("Đăng nhập Pixiv thành công qua web")
            if api.refresh_token:
                with open("config.py", "a") as f:
                    f.write(f"\nPIXIV_REFRESH_TOKEN = \"{api.refresh_token}\"\n")
                logging.info("Đã lưu refresh token vào config.py")
    except Exception as e:
        logging.error(f"Lỗi khi đăng nhập Pixiv: {str(e)}")
        return

    try:
        logging.info("Gọi API illust_recommended...")
        json_result = await api.illust_recommended()
        illustrations = json_result.illusts[:10]  # Lấy 5 tác phẩm đầu tiên
        logging.info(f"Đã nhận được {len(illustrations)} tác phẩm từ Pixiv")

        sent_count = 0
        headers = {
            'Referer': 'https://www.pixiv.net/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/*'
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            for idx, illust in enumerate(illustrations):
                # Log chi tiết cấu trúc dữ liệu để debug
                logging.debug(f"Chi tiết tác phẩm {illust.title}: keys={illust.keys()}")
                
                # Trích xuất URL ảnh, ưu tiên kích thước nhỏ hơn cho embed
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
                    logging.warning(f"Bỏ qua tác phẩm {illust.title}: Không tìm thấy URL ảnh. "
                                  f"meta_single_page={illust.meta_single_page if 'meta_single_page' in illust else 'Không có'}, "
                                  f"meta_pages={len(illust.meta_pages) if 'meta_pages' in illust else 'Không có'}, "
                                  f"image_urls={illust.image_urls.keys() if 'image_urls' in illust else 'Không có'}")
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

                try:
                    # Tải ảnh và gửi dưới dạng file để đảm bảo hiển thị
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
                except Exception as e:
                    logging.error(f"Lỗi khi tải và gửi file cho {illust.title}: {str(e)}")
                    continue
                await asyncio.sleep(1)

        logging.info(f"Hoàn tất xử lý và gửi {sent_count} ảnh")
    except Exception as e:
        logging.error(f"Lỗi khi lấy ảnh từ Pixiv: {str(e)}")

async def x_images_task(bot):
    """Tác vụ nền kiểm tra ảnh từ Pixiv mỗi 15 phút."""
    logging.info("Khởi động tác vụ lấy ảnh từ Pixiv")
    while True:
        try:
            await fetch_and_post_x_images(bot)
        except Exception as e:
            logging.error(f"Lỗi trong x_images_task: {str(e)}")
        logging.info("Hoàn thành chu kỳ lấy ảnh từ Pixiv, chờ 15 phút")
        await asyncio.sleep(900)