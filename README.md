# yoombot
[To-do list](https://docs.google.com/spreadsheets/d/1bn4rU957q-AAq0J2euaXHhaUvOfMbPnhTEufp4CEu5U/edit?usp=sharing)

Hướng dẫn cài đặt
---
1. Clone repo về máy và cài đặt requirements.txt.
2. Tạo file .env bao gồm: BOT_TOKEN, GROQ_API_KEY, PIXIV_REFRESH_TOKEN (phải ghi, nhưng có thể để trống) và các ID channel discord bao gồm 
MENTAL_CHANNEL_ID, GENERAL_CHANNEL_ID, NEWS_CHANNEL_ID, IMAGE_CHANNEL_ID, WELCOME_CHANNEL_ID.
3. Lưu các file PDF cần thiết vào data/documents/mental_counseling/ để chạy chatbot tư vấn tâm lý.
4. Chạy file main.py.
5. Khi chạy lần đầu, terminal sẽ yêu cầu đăng nhập vào pixiv. Hãy làm theo các bước [như sau](https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362)
 để hoàn tất việc đăng nhập. Key sẽ được tự động lưu vào config.py và những lần chạy sau sẽ không cần đăng nhập lại.

Chức năng (WIP)
---
1. Tự động hiển thị thông báo chào mừng khi có người join server.
2. Phát nhạc từ Youtube thông qua link, tên bài hát hay link playlist.
3. Tự động đăng báo mới từ VnExpress mỗi 15 phút.
4. Tự động đăng hình từ Home của tài khoản đăng nhập pixiv.
5. Chatbot AI, bao gồm chatbot tư vấn tâm lý và chatbot tổng hợp

Hướng dẫn sử dụng
---
Chatbot: chatbot sẽ tự động đọc tin nhắn trong kênh có ID được ghi trong .env và phản hồi, ngoài ra sẽ không phản hồi trên kênh nào khác.

Các chức năng tự động sẽ thực hiện tự động khi khởi chạy chương trình.

Danh sách lệnh chức năng đăng ảnh (!):

| Commands          | Nội dung |
|--------------------|-------------------|
|  add_artist        | Thêm artist muốn theo dõi  |
|  remove_artist     | Xoá artist muốn theo dõi  |
|  add_tag           | Thêm tag muốn theo dõi  |
|  remove_tag        | Xoá tag muốn theo dõi  |
|  post_image_now    | Xuất thêm 10 ảnh  |
---------------------------------------------------

Danh sách lệnh chức năng phát nhạc (!):

| Commands          | Nội dung |
|--------------------|-------------------|
|  clear_cache       | Xóa cache yt-dlp  |
|  debug             | Hiển thị thông tin debug  |
|  ffmpeg_test       | Test FFmpeg  |
|  force_reconnect   | Buộc kết nối lại voice  |
|  help              | Shows this message  |
|  join              | Tham gia kênh voice của người dùng  |
|  leave             | Rời khỏi kênh voice  |
|  now               | Hiển thị bài hát đang phát  |
|  pause             | Tạm dừng bài hát đang phát|
|  play              | Phát nhạc từ URL YouTube hoặc tìm kiếm theo từ khóa  |
|  queue             | Hiển thị danh sách queue nhạc hiện tại|
|  resume            | Tiếp tục phát bài hát đã tạm dừng  |
|  search            | Tìm kiếm bài hát mà không phát (để debug)  |
|  skip              | Bỏ qua bài hát hiện tại  |
|  stop              | Dừng phát nhạc và xóa queue  |
|  test_stream       | Test stream URL cho debug  |
|  voice_debug       | Debug thông tin voice connection |
-------------------------------------------------------

Cấu trúc đường dẫn
---
yoombot/

├── data/

│   ├── documents/          # Chứa file PDF, JSON và JSONL cho mô hình RAG

│   │   └── mental_counseling/

│   ├── chat_history.db

│   ├── queues.db

│   └── yt_dlp_cache/

├── src/

│   ├── music/

│   │   ├── __init__.py

│   │   ├── player.py

│   │   └── utils.py

│   ├── commands/

│   │   ├── __init__.py

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

│   │   └── pixiv.py

│   └──__init__.py

├── main.py

├── config.py

├── database.py

└── .env
