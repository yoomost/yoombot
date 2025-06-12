# yoombot
[To-do list](https://docs.google.com/spreadsheets/d/1bn4rU957q-AAq0J2euaXHhaUvOfMbPnhTEufp4CEu5U/edit?usp=sharing)

Lệnh phát nhạc bot:

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
|  voice_debug       | Debug thông tin voice connectio|
-------------------------------------------------------

Cấu trúc đường dẫn
---
discord_bot/

├── data/

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

│   │   └── helpers.py

│   └──__init__.py

├── main.py

├── config.py

├── database.py

└── .env
