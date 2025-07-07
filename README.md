# yoombot

[To-do list](https://docs.google.com/spreadsheets/d/1bn4rU957q-AAq0J2euaXHhaUvOfMbPnhTEufp4CEu5U/edit?usp=sharing)

## Hướng dẫn cài đặt

1.  Clone repo về máy và cài đặt `requirements.txt`.
2.  Tạo file `.env` bao gồm:
      * `BOT_TOKEN`, `GROQ_API_KEY` (cho chatbot từ Groq API)
      * `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` (từ việc [tạo reddit app](https://www.reddit.com/prefs/apps))
      * `PIXIV_REFRESH_TOKEN` (phải ghi, nhưng có thể để trống)
      * [cite\_start]ID channel discord: `MENTAL_CHANNEL_ID`, `GENERAL_CHANNEL_ID`, `NEWS_CHANNEL_ID`, `IMAGE_CHANNEL_ID`, `WELCOME_CHANNEL_ID` [cite: 2][cite\_start], `WIKI_CHANNEL_ID` [cite: 5][cite\_start], `EDUCATIONAL_CHANNEL_ID`[cite: 5].
        [cite\_start]Thay các ID trên bằng ID thực tế của các kênh trong server Discord của bạn[cite: 5].
3.  Lưu các file PDF cần thiết vào `data/documents/mental_counseling/` để chạy chatbot tư vấn tâm lý.
4.  Chạy file `main.py`.
5.  Khi chạy lần đầu, terminal sẽ yêu cầu đăng nhập vào pixiv. Hãy làm theo các bước [như sau](https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362) để hoàn tất việc đăng nhập. Key sẽ được tự động lưu vào `config.py` và những lần chạy sau sẽ không cần đăng nhập lại.


## Chức năng (WIP)

1.  Tự động hiển thị thông báo chào mừng khi có người join server.
2.  Phát nhạc từ Youtube thông qua link, tên bài hát hay link playlist.
3.  Tự động đăng báo mới từ VnExpress mỗi 15 phút.
4.  Tự động đăng hình Recommended của tài khoản đăng nhập pixiv, có thể thay đổi theo artist hay tag.
5.  Tự động đăng hình sắp xếp theo Hot trên subreddit you-know-which, có thể chọn nguồn từ user bất kì trong subreddit.
6.  Chatbot AI, bao gồm chatbot tư vấn tâm lý và chatbot tổng hợp.
7.  [cite\_start]Hỗ trợ tra cứu tài liệu học tập và giải bài tập[cite: 2].

## Hướng dẫn sử dụng

Chatbot: chatbot sẽ tự động đọc tin nhắn trong kênh có ID được ghi trong `.env` và phản hồi, ngoài ra sẽ không phản hồi trên kênh nào khác.

Các chức năng tự động sẽ thực hiện tự động khi khởi chạy chương trình.

### Danh sách lệnh chức năng đăng ảnh (\!):

| Commands | Nội dung |
| :------------------ | :---------------- |
| `add_artist` | Thêm artist muốn theo dõi |
| `remove_artist` | Xoá artist muốn theo dõi |
| `add_reddit_user` | Thêm user muốn theo dõi |
| `remove_reddit_user` | Xoá user muốn theo dõi |
| `add_tag` | Thêm tag muốn theo dõi |
| `remove_tag` | Xoá tag muốn theo dõi |
| `post_image_now` | Xuất thêm 10 ảnh |

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
| `play` | Phát nhạc từ URL YouTube hoặc tìm kiếm theo từ khóa |
| `queue` | Hiển thị danh sách queue nhạc hiện tại |
| `resume` | Tiếp tục phát bài hát đã tạm dừng |
| `search` | Tìm kiếm bài hát mà không phát (để debug) |
| `skip` | Bỏ qua bài hát hiện tại |
| `stop` | Dừng phát nhạc và xóa queue |
| `test_stream` | Test stream URL cho debug |
| `voice_debug` | Debug thông tin voice connection |

### Danh sách lệnh học tập (\!):

[cite\_start]Các lệnh học tập được thiết kế để hoạt động trong các kênh cụ thể[cite: 3].

#### 1\. Lệnh `!khan <chủ đề>`

  * [cite\_start]**Mô tả**: Tra cứu bài giảng hoặc video từ Khan Academy dựa trên chủ đề được yêu cầu[cite: 6].
  * [cite\_start]**Kênh hoạt động**: Chỉ hoạt động trong kênh có ID `EDUCATIONAL_CHANNEL_ID` (kênh học tập)[cite: 7].
  * [cite\_start]**Cú pháp**: `!khan <chủ đề>` [cite: 8]
  * **Ví dụ**:
      * [cite\_start]Nhập: `!khan quadratic equation` [cite: 8]
      * Kết quả:
        ```
        **Chủ đề: Quadratic equation**
        Xem bài giảng/video tại: https://www.khanacademy.org/math/algebra/x2f8bb11595b61c86:quadratic-functions-equations
        Nguồn: Khan Academy
        ```
  * **Chủ đề hỗ trợ**:
      * [cite\_start]`quadratic equation` (phương trình bậc hai) [cite: 8]
      * [cite\_start]`derivative` (đạo hàm) [cite: 8]
      * [cite\_start]`photosynthesis` (quang hợp) [cite: 8]
      * [cite\_start]`newton's laws` (định luật Newton) [cite: 8]
      * [cite\_start](Danh sách sẽ được mở rộng trong tương lai) [cite: 8]
  * **Lưu ý**:
      * [cite\_start]Nếu chủ đề không được tìm thấy, bot sẽ yêu cầu thử lại với từ khóa khác[cite: 9].
      * [cite\_start]Ví dụ lỗi: `!khan calculus` → "Không tìm thấy tài liệu cho chủ đề này. Vui lòng thử lại với từ khóa khác, ví dụ: `!khan quadratic equation`." [cite: 9]
      * [cite\_start]Hiện tại chỉ hỗ trợ một số chủ đề cố định[cite: 20]. [cite\_start]Danh sách chủ đề sẽ được cập nhật trong tương lai[cite: 21].

#### 2\. Lệnh `!math <phương trình>`

  * [cite\_start]**Mô tả**: Giải phương trình toán học sử dụng thư viện SymPy (hỗ trợ phương trình, đạo hàm, tích phân, v.v.)[cite: 10].
  * [cite\_start]**Kênh hoạt động**: Chỉ hoạt động trong kênh có ID `EDUCATIONAL_CHANNEL_ID` (kênh học tập)[cite: 11].
  * [cite\_start]**Cú pháp**: `!math <phương trình>` [cite: 12]
  * **Ví dụ**:
      * [cite\_start]Nhập: `!math x^2 + 5x + 6 = 0` [cite: 12]
      * Kết quả:
        ```
        **Kết quả giải phương trình**
        **Phương trình**: x^2 + 5x + 6
        **Nghiệm**: x = -2, x = -3
        Nguồn: SymPy
        ```
      * [cite\_start]Nhập: `!math 2*x + 3` [cite: 12]
      * Kết quả:
        ```
        **Kết quả giải phương trình**
        **Phương trình**: 2*x + 3
        **Nghiệm**: x = -3/2 [cite: 13]
        Nguồn: SymPy
        ```
  * **Lưu ý**:
      * [cite\_start]Phương trình cần sử dụng biến `x` và cú pháp toán học chuẩn (ví dụ: `x^2` cho bình phương, `*` cho phép nhân)[cite: 14].
      * Nếu nhập sai cú pháp, bot sẽ báo lỗi và gợi ý: `Lỗi khi giải phương trình: <lỗi>. Vui lòng nhập đúng cú pháp, ví dụ: !math x^2 + 5x + 6 = 0`[cite: 15].
      * [cite\_start]Chỉ hỗ trợ phương trình với biến `x` và yêu cầu cú pháp chuẩn[cite: 22]. [cite\_start]Các bài toán phức tạp hơn (như tích phân hoặc hệ phương trình nhiều biến) sẽ được hỗ trợ trong các phiên bản sau[cite: 23].

#### 3\. Lệnh `!wikipedia <truy vấn>`

  * [cite\_start]**Mô tả**: Tra cứu tóm tắt từ Wikipedia cho một chủ đề hoặc khái niệm[cite: 16].
  * [cite\_start]**Kênh hoạt động**: Chỉ hoạt động trong kênh có ID `WIKI_CHANNEL_ID` (kênh Wikipedia)[cite: 17].
  * [cite\_start]**Cú pháp**: `!wikipedia <truy vấn>` [cite: 18]
  * **Ví dụ**:
      * [cite\_start]Nhập: `!wikipedia photosynthesis` [cite: 18]
      * Kết quả:
        ```
        **Tóm tắt: Photosynthesis**
        Photosynthesis is a process used by plants and other organisms to convert light energy into chemical energy that, through cellular respiration, can later be released to fuel the organisms' activities...
        Nguồn: Wikipedia
        ```
  * **Lưu ý**:
      * [cite\_start]Truy vấn nên cụ thể để có kết quả chính xác (ví dụ: `photosynthesis` thay vì `plant`)[cite: 19].
      * Nếu không tìm thấy kết quả, bot sẽ thông báo: `Không tìm thấy tóm tắt cho truy vấn này. Vui lòng thử lại.`[cite: 19, 20].
      * [cite\_start]Kết quả có thể không chính xác nếu truy vấn không rõ ràng[cite: 24]. [cite\_start]Hãy sử dụng từ khóa cụ thể[cite: 25].

## Lỗi thường gặp và cách khắc phục

  * **Lệnh không hoạt động**:
      * [cite\_start]Kiểm tra xem bạn đang sử dụng đúng kênh (`EDUCATIONAL_CHANNEL_ID` cho `!khan` và `!math`, `WIKI_CHANNEL_ID` cho `!wikipedia`)[cite: 26].
      * [cite\_start]Ví dụ lỗi: `Lệnh này chỉ hoạt động trong kênh học tập.` [cite: 26]
  * **Lỗi cú pháp phương trình**:
      * [cite\_start]Đảm bảo sử dụng cú pháp toán học đúng, ví dụ: `x^2 + 5x + 6 = 0` thay vì `x squared plus 5x plus 6`[cite: 27].
  * **Không tìm thấy tài liệu**:
      * [cite\_start]Kiểm tra từ khóa (ví dụ: dùng `quadratic equation` thay vì `math` cho `!khan`)[cite: 28].
      * [cite\_start]Thử từ khóa khác hoặc cụ thể hơn cho `!wikipedia`[cite: 28].

## Cấu trúc đường dẫn

```
yoombot/
├── data/
│   ├── documents/          # Chứa file PDF, JSON và JSONL cho mô hình RAG
│   │   └── mental_counseling/
│   ├── bot.log [cite: 4]
│   ├── rag_index/ [cite: 4]
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
│   │   ├── commands.py [cite: 4]
│   │   ├── music_commands.py [cite: 4]
│   │   └── debug_commands.py [cite: 4]
│   ├── events/
│   │   ├── __init__.py
│   │   └── bot_events.py [cite: 4]
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── helpers.py [cite: 4]
│   │   ├── news.py [cite: 4]
│   │   ├── rag.py [cite: 4]
│   │   ├── reddit.py [cite: 4]
│   │   └── pixiv.py [cite: 4]
│   └──__init__.py
├── main.py [cite: 4]
├── config.py [cite: 4]
├── database.py [cite: 4]
└── .env
```
