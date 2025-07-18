# Yoombot

Một chiếc bot Discord đa chức năng kết hợp trò chuyện AI, phát nhạc và đăng nội dung tự động. Bot cũng hỗ trợ tư vấn sức khỏe tâm thần thông qua AI dựa trên tài liệu, các truy vấn toán học và khoa học, cùng các công cụ giáo dục như Khan Academy và tìm kiếm Wikipedia.

## Hướng dẫn cài đặt

1.  Clone repo, tạo venv và cài đặt `requirements.txt`.
2.  Tạo file `.env` như `env_example.md`.
3.  Lưu các file PDF, JSON và JSONL cần thiết vào `data/documents/mental_counseling/` để chạy chatbot tư vấn tâm lý.
4.  Chạy file `main.py`.
5.  Khi chạy lần đầu, terminal sẽ yêu cầu đăng nhập vào pixiv. Hãy làm theo các bước [như sau](https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362) để hoàn tất việc đăng nhập. Key sẽ được tự động lưu vào `config.py` và những lần chạy sau sẽ không cần đăng nhập lại.
6. Chạy lệnh sau để tạo file spec và app:
      ```
      pyinstaller --clean --noconfirm --onefile --noconsole --icon=icon.ico --add-data "data;data" --add-data "src;src" --add-data ".env;." --add-data "main.py;." --add-data "config.py;." --add-data "database.py;." --add-data "cookies.txt;." --add-data "icon.ico;." --hidden-import "yt_dlp" --hidden-import "requests" --hidden-import "pystray" --hidden-import "PIL" logger_gui.py
      ```
7. Khởi chạy app: `dist\logger_gui.py`

## Chức năng (WIP)

1.  Gửi tin nhắn chào mừng thành viên mới.
2.  Phát nhạc từ Youtube thông qua link, tên bài hát hay link playlist.
3.  Tự động đăng báo mới từ VnExpress mỗi 15 phút.
4.  Tự động đăng hình Recommended của tài khoản đăng nhập pixiv, có thể thay đổi theo artist hay tag.
5.  Tự động đăng hình sắp xếp theo Hot trên subreddit you-know-which, có thể chọn nguồn từ user bất kì trong subreddit.
6.  Chatbot AI, bao gồm chatbot tư vấn tâm lý RAG, chatbot tổng hợp từ Groq API, và chatbot Grok 4.
7.  Hỗ trợ tra cứu tài liệu học tập và giải bài tập.


## Hướng dẫn sử dụng

Chatbot: chatbot sẽ tự động đọc tin nhắn trong kênh có ID được ghi trong `.env` và phản hồi, ngoài ra sẽ không phản hồi trên kênh nào khác.

Các chức năng tự động sẽ thực hiện tự động khi khởi chạy chương trình.

### Danh sách lệnh chức năng đăng ảnh (\!):

| Commands | Nội dung |
| :------------------ | :---------------- |
| `add_artist <ID artist>` | Thêm artist muốn theo dõi |
| `remove_artist <ID artist>` | Xoá artist muốn theo dõi |
| `add_reddit_user <username>` | Thêm user muốn theo dõi |
| `remove_reddit_user <username>` | Xoá user muốn theo dõi |
| `add_reddit_flair <flair>` | Thêm flair Reddit muốn theo dõi |
| `remove_reddit_flair <flair>` | Xoá flair Reddit muốn theo dõi |
| `add_subreddit <tên subreddit (không lấy phần "r/")>` | Thêm subreddit muốn theo dõi |
| `remove_subreddit <tên subreddit (không lấy phần "r/")>` | Xoá subreddit muốn theo dõi |
| `add_tag <tag>` | Thêm tag muốn theo dõi |
| `remove_tag <tag>` | Xoá tag muốn theo dõi |
| `post_image_now` | Xuất thêm 10 ảnh từ pixiv|
| `post_reddit_images_now` | Xuất thêm 5 ảnh từ Reddit|

### Danh sách lệnh chức năng phát nhạc (\!):

| Commands | Nội dung |
| :---------------- | :-------------------------- |
| `clear_cache` | Xóa cache yt-dlp |
| `debug` | Hiển thị thông tin debug |
| `ffmpeg_test` | Test FFmpeg |
| `force_reconnect` | Buộc kết nối lại voice |
| `help` | Shows this message |
| `join` | Tham gia kênh voice của người dùng |
| `leave` | Rời khỏi kênh voice |
| `now` | Hiển thị bài hát đang phát |
| `pause` | Tạm dừng bài hát đang phát |
| `play <tên/link>` | Phát nhạc từ URL YouTube hoặc tìm kiếm theo từ khóa |
| `queue` | Hiển thị danh sách queue nhạc hiện tại |
| `resume` | Tiếp tục phát bài hát đã tạm dừng |
| `search <tên/link>` | Tìm kiếm bài hát mà không phát (để debug) |
| `skip` | Bỏ qua bài hát hiện tại |
| `stop` | Dừng phát nhạc và xóa queue |
| `test_stream` | Test stream URL cho debug |
| `voice_debug` | Debug thông tin voice connection |

### Chatbot Grok 4 (xAI)

| Commands | Nội dung |
| :---------------- | :-------------------------- |
|`!grok <truy vấn>` | Chế độ mặc định |
|`!grok deepsearch <truy vấn>` | Tìm dữ liệu web + X (Twitter) |
|`!grok deepersearch <truy vấn>` | Suy luận chuyên sâu |
|`!grok think <truy vấn>` | Lập luận từng bước, có hệ thống |



### Danh sách lệnh học tập (\!):

Các lệnh học tập được thiết kế để hoạt động trong các kênh cụ thể.

#### 1\. Lệnh `!khan <chủ đề>`

  * **Mô tả**: Tra cứu bài giảng hoặc video từ Khan Academy dựa trên chủ đề được yêu cầu.
  * **Kênh hoạt động**: Chỉ hoạt động trong kênh có ID `EDUCATIONAL_CHANNEL_ID` (kênh học tập).
  * **Cú pháp**: `!khan <chủ đề>` 
  * **Ví dụ**:
      * Nhập: `!khan quadratic equation` 
      * Kết quả:
        ```
        **Chủ đề: Quadratic equation**
        Xem bài giảng/video tại: https://www.khanacademy.org/math/algebra/x2f8bb11595b61c86:quadratic-functions-equations
        Nguồn: Khan Academy
        ```
  * **Chủ đề hỗ trợ**:
      * `quadratic equation` (phương trình bậc hai) 
      * `derivative` (đạo hàm) 
      * `photosynthesis` (quang hợp) 
      * `newton's laws` (định luật Newton) 
      * (Danh sách sẽ được mở rộng trong tương lai) 
  * **Lưu ý**:
      * Nếu chủ đề không được tìm thấy, bot sẽ yêu cầu thử lại với từ khóa khác.
      * Ví dụ lỗi: `!khan calculus` → "Không tìm thấy tài liệu cho chủ đề này. Vui lòng thử lại với từ khóa khác, ví dụ: `!khan quadratic equation`." 
      * Hiện tại chỉ hỗ trợ một số chủ đề cố định. Danh sách chủ đề sẽ được cập nhật trong tương lai.

#### 2\. Lệnh `!math <phương trình>`

  * **Mô tả**: Giải phương trình toán học sử dụng thư viện SymPy (hỗ trợ phương trình, đạo hàm, tích phân, v.v.).
  * **Kênh hoạt động**: Chỉ hoạt động trong kênh có ID `EDUCATIONAL_CHANNEL_ID` (kênh học tập).
  * **Cú pháp**: `!math <phương trình>` 
  * **Ví dụ**:
      * Nhập: `!math x^2 + 5x + 6 = 0` 
      * Kết quả:
        ```
        **Kết quả giải phương trình**
        **Phương trình**: x^2 + 5x + 6
        **Nghiệm**: x = -2, x = -3
        Nguồn: SymPy
        ```
      * Nhập: `!math 2*x + 3` 
      * Kết quả:
        ```
        **Kết quả giải phương trình**
        **Phương trình**: 2*x + 3
        **Nghiệm**: x = -3/2 
        Nguồn: SymPy
        ```
  * **Lưu ý**:
      * Phương trình cần sử dụng biến `x` và cú pháp toán học chuẩn (ví dụ: `x^2` cho bình phương, `*` cho phép nhân).
      * Nếu nhập sai cú pháp, bot sẽ báo lỗi và gợi ý: `Lỗi khi giải phương trình: <lỗi>. Vui lòng nhập đúng cú pháp, ví dụ: !math x^2 + 5x + 6 = 0`.
      * Chỉ hỗ trợ phương trình với biến `x` và yêu cầu cú pháp chuẩn. Các bài toán phức tạp hơn (như tích phân hoặc hệ phương trình nhiều biến) sẽ được hỗ trợ trong các phiên bản sau.

#### 3\. Lệnh `!wikipedia <truy vấn>`

  * **Mô tả**: Tra cứu tóm tắt từ Wikipedia cho một chủ đề hoặc khái niệm.
  * **Kênh hoạt động**: Chỉ hoạt động trong kênh có ID `WIKI_CHANNEL_ID` (kênh Wikipedia).
  * **Cú pháp**: `!wikipedia <truy vấn>` 
  * **Ví dụ**:
      * Nhập: `!wikipedia photosynthesis` 
      * Kết quả:
        ```
        **Tóm tắt: Photosynthesis**
        Photosynthesis is a process used by plants and other organisms to convert light energy into chemical energy that, through cellular respiration, can later be released to fuel the organisms' activities...
        Nguồn: Wikipedia
        ```
  * **Lưu ý**:
      * Truy vấn nên cụ thể để có kết quả chính xác (ví dụ: `photosynthesis` thay vì `plant`).
      * Nếu không tìm thấy kết quả, bot sẽ thông báo: `Không tìm thấy tóm tắt cho truy vấn này. Vui lòng thử lại.`.
      * Kết quả có thể không chính xác nếu truy vấn không rõ ràng. Hãy sử dụng từ khóa cụ thể.

## Lỗi thường gặp và cách khắc phục

  * **Lệnh không hoạt động**:
      * Kiểm tra xem bạn đang sử dụng đúng kênh (`EDUCATIONAL_CHANNEL_ID` cho `!khan` và `!math`, `WIKI_CHANNEL_ID` cho `!wikipedia`).
      * Ví dụ lỗi: `Lệnh này chỉ hoạt động trong kênh học tập.` 
  * **Lỗi cú pháp phương trình**:
      * Đảm bảo sử dụng cú pháp toán học đúng, ví dụ: `x^2 + 5x + 6 = 0` thay vì `x squared plus 5x plus 6`.
  * **Không tìm thấy tài liệu**:
      * Kiểm tra từ khóa (ví dụ: dùng `quadratic equation` thay vì `math` cho `!khan`).
      * Thử từ khóa khác hoặc cụ thể hơn cho `!wikipedia`.

## Cấu trúc đường dẫn

```
yoombot/
├── data/
│   ├── documents/              # Chứa file PDF, JSON và JSONL cho mô hình RAG
│   │   └── mental_counseling/
│   ├── bot.log 
│   ├── rag_index/ 
│   ├── chat_history.db
│   ├── queues.db
│   └── yt_dlp_cache/
├── dist/                       # Sau khi chạy app sẽ xuất hiện
├── src/
│   ├── music/
│   │   ├── __init__.py
│   │   ├── player.py
│   │   └── utils.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── commands.py 
│   │   ├── music_commands.py 
│   │   └── debug_commands.py 
│   ├── events/
│   │   ├── __init__.py
│   │   └── bot_events.py 
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── helpers.py 
│   │   ├── news.py 
│   │   ├── rag.py 
│   │   ├── reddit.py 
│   │   └── pixiv.py 
│   └──__init__.py
├── main.py 
├── config.py 
├── database.py 
├── logger_gui.py 
├── icon.ico 
└── .env
```
