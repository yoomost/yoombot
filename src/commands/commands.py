from discord.ext import commands
import discord
from config import EDUCATIONAL_CHANNEL_ID, WIKI_CHANNEL_ID
from sympy import solve, symbols, sympify
import requests
import logging

# Danh sách URL tĩnh cho Khan Academy
KHAN_ACADEMY_RESOURCES = {
    "quadratic equation": "https://www.khanacademy.org/math/algebra/x2f8bb11595b61c86:quadratic-functions-equations",
    "derivative": "https://www.khanacademy.org/math/calculus-1/cs1-derivatives-definition-and-basic-rules",
    "photosynthesis": "https://www.khanacademy.org/science/biology/photosynthesis",
    "newton's laws": "https://www.khanacademy.org/science/physics/forces-newtons-laws"
    # Thêm các chủ đề khác tại đây
}

class EducationalCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='khan')
    @commands.check(lambda ctx: ctx.channel.id == EDUCATIONAL_CHANNEL_ID)
    async def khan_command(self, ctx, *, topic):
        """Tra cứu bài giảng hoặc video từ Khan Academy theo chủ đề."""
        try:
            topic = topic.lower().strip()
            resource_url = KHAN_ACADEMY_RESOURCES.get(topic)
            if resource_url:
                embed = discord.Embed(
                    title=f"Chủ đề: {topic.capitalize()}",
                    description=f"Xem bài giảng/video tại: {resource_url}",
                    color=0x00ff00
                )
                embed.set_footer(text="Nguồn: Khan Academy")
                await ctx.send(embed=embed)
                logging.info(f"Đã trả về tài liệu Khan Academy cho chủ đề: {topic}")
            else:
                await ctx.send("Không tìm thấy tài liệu cho chủ đề này. Vui lòng thử lại với từ khóa khác, ví dụ: `!khan quadratic equation`.")
                logging.warning(f"Không tìm thấy tài liệu Khan Academy cho chủ đề: {topic}")
        except Exception as e:
            await ctx.send(f"Lỗi khi tra cứu Khan Academy: {str(e)}")
            logging.error(f"Lỗi khi tra cứu Khan Academy: {str(e)}")

    @commands.command(name='math')
    @commands.check(lambda ctx: ctx.channel.id == EDUCATIONAL_CHANNEL_ID)
    async def math_command(self, ctx, *, equation):
        """Giải phương trình toán học sử dụng SymPy."""
        try:
            x = symbols('x')
            # Làm sạch chuỗi phương trình và chuyển về dạng f(x) = 0
            equation = equation.strip()
            if '=' in equation:
                left, right = equation.split('=')
                left = left.strip()
                right = right.strip()
                # Tránh thêm dấu ngoặc thừa, chỉ sử dụng nếu cần
                if right == '0':
                    eq_str = left
                else:
                    eq_str = f"{left} - {right}"
            else:
                eq_str = equation  # Nếu không có dấu '=', giả định phương trình = 0
            eq = sympify(eq_str)
            solutions = solve(eq, x)
            if solutions:
                response = f"**Phương trình**: {equation}\n**Nghiệm**: {', '.join(str(sol) for sol in solutions)}"
            else:
                response = "Không tìm thấy nghiệm."
            embed = discord.Embed(
                title="Kết quả giải phương trình",
                description=response,
                color=0x00ff00
            )
            embed.set_footer(text="Nguồn: SymPy")
            await ctx.send(embed=embed)
            logging.info(f"Đã giải phương trình: {equation}")
        except Exception as e:
            await ctx.send(
                f"Lỗi khi giải phương trình: {str(e)}. "
                "Vui lòng đảm bảo cú pháp đúng, ví dụ: `!math x^2 + 5*x + 6 = 0`. "
                "Lưu ý: sử dụng `*` cho phép nhân, `^` cho lũy thừa."
            )
            logging.error(f"Lỗi khi giải phương trình: {str(e)}")

    @commands.command(name='wikipedia')
    @commands.check(lambda ctx: ctx.channel.id == WIKI_CHANNEL_ID)
    async def wikipedia_command(self, ctx, *, query):
        """Tra cứu tóm tắt từ Wikipedia."""
        try:
            search_url = "https://en.wikipedia.org/w/api.php"
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "origin": "*"
            }
            search_response = requests.get(search_url, params=search_params, timeout=5)
            search_response.raise_for_status()
            search_data = search_response.json()
            
            if "query" in search_data and "search" in search_data["query"] and search_data["query"]["search"]:
                first_title = search_data["query"]["search"][0]["title"]
                extract_url = "https://en.wikipedia.org/w/api.php"
                extract_params = {
                    "action": "query",
                    "prop": "extracts",
                    "exintro": True,
                    "explaintext": True,
                    "titles": first_title,
                    "format": "json",
                    "origin": "*"
                }
                extract_response = requests.get(extract_url, params=extract_params, timeout=5)
                extract_response.raise_for_status()
                extract_data = extract_response.json()
                
                if "query" in extract_data and "pages" in extract_data["query"]:
                    pages = extract_data["query"]["pages"]
                    for page_id, page in pages.items():
                        if "extract" in page:
                            summary = page["extract"][:1000] + "..."  # Tăng giới hạn lên 1000 ký tự
                            embed = discord.Embed(
                                title=f"Tóm tắt: {query}",
                                description=summary,
                                color=0x00ff00
                            )
                            embed.set_footer(text="Nguồn: Wikipedia")
                            await ctx.send(embed=embed)
                            logging.info(f"Đã trả về tóm tắt Wikipedia cho truy vấn: {query}")
                            return
            await ctx.send("Không tìm thấy tóm tắt cho truy vấn này. Vui lòng thử lại với từ khóa cụ thể hơn.")
            logging.warning(f"Không tìm thấy tóm tắt Wikipedia cho truy vấn: {query}")
        except Exception as e:
            await ctx.send(f"Lỗi khi tra cứu Wikipedia: {str(e)}")
            logging.error(f"Lỗi khi tra cứu Wikipedia: {str(e)}")

async def setup(bot):
    await bot.add_cog(EducationalCommands(bot))