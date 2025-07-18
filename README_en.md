# Yoombot

A multifunctional Discord bot that combines AI-powered chat, music playback, and automated content posting. It also supports mental health counseling through document-based AI, math and science queries, and educational tools like Khan Academy and Wikipedia search.

## Installation Instructions

1. Clone the repository, create a virtual environment, and install dependencies from `requirements.txt`.
2. Create a `.env` file based on `env_example.md`.
3. Place required PDF, JSON, and JSONL files in `data/documents/mental_counseling/` to run the mental health counseling chatbot.
4. Run `main.py`.
5. On the first run, the terminal will prompt for pixiv login. Follow the steps [here](https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362) to complete the login. The key will be automatically saved to `config.py`, and subsequent runs will not require re-login.
6. Run the following command to create the spec file and app:
   ```
   pyinstaller --clean --noconfirm --onefile --noconsole --icon=icon.ico --add-data "data;data" --add-data "src;src" --add-data ".env;." --add-data "main.py;." --add-data "config.py;." --add-data "database.py;." --add-data "cookies.txt;." --add-data "icon.ico;." --hidden-import "yt_dlp" --hidden-import "requests" --hidden-import "pystray" --hidden-import "PIL" logger_gui.py
   ```
7. Launch the app: `dist\logger_gui.py`

## Features (Work in Progress)

1. Send welcome messages to new members.
2. Play music from YouTube via link, song name, or playlist link.
3. Automatically post news from VnExpress every 15 minutes.
4. Automatically post recommended images from the logged-in pixiv account, customizable by artist or tag.
5. Automatically post images sorted by Hot from a specific subreddit, with the option to select sources from any user in the subreddit.
6. AI chatbot, including a RAG-based mental health counseling bot, a general chatbot using Groq API, and a Grok 4 chatbot.
7. Support for educational material lookup and homework assistance.

## Usage Instructions

**Chatbot**: The chatbot automatically reads and responds to messages in the channel specified by the ID in the `.env` file. It will not respond in other channels.

Automated features will run automatically upon program startup.

### Image Posting Commands (\!):

| Commands | Description |
| :------------------ | :---------------- |
| `add_artist <artist ID>` | Add an artist to follow |
| `remove_artist <artist ID>` | Remove an artist from following |
| `add_reddit_user <username>` | Add a Reddit user to follow |
| `remove_reddit_user <username>` | Remove a Reddit user from following |
| `add_reddit_flair <flair>` | Add a Reddit flair to follow |
| `remove_reddit_flair <flair>` | Remove a Reddit flair from following |
| `add_subreddit <subreddit name (without "r/")>` | Add a subreddit to follow |
| `remove_subreddit <subreddit name (without "r/")>` | Remove a subreddit from following |
| `add_tag <tag>` | Add a tag to follow |
| `remove_tag <tag>` | Remove a tag from following |
| `post_image_now` | Post 10 additional images from pixiv |
| `post_reddit_images_now` | Post 5 additional images from Reddit |

### Music Playback Commands (\!):

| Commands | Description |
| :---------------- | :-------------------------- |
| `clear_cache` | Clear yt-dlp cache |
| `debug` | Display debug information |
| `ffmpeg_test` | Test FFmpeg |
| `force_reconnect` | Force reconnect to voice channel |
| `help` | Show this message |
| `join` | Join the user's voice channel |
| `leave` | Leave the voice channel |
| `now` | Display the currently playing song |
| `pause` | Pause the currently playing song |
| `play <name/link>` | Play music from a YouTube URL or search by keyword |
| `queue` | Display the current music queue |
| `resume` | Resume a paused song |
| `search <name/link>` | Search for a song without playing (for debugging) |
| `skip` | Skip the current song |
| `stop` | Stop music playback and clear the queue |
| `test_stream` | Test stream URL for debugging |
| `voice_debug` | Debug voice connection information |

### Grok 4 Chatbot (xAI)

| Commands | Description |
| :---------------- | :-------------------------- |
| `!grok <query>` | Default mode |
| `!grok deepsearch <query>` | Search web + X (Twitter) data |
| `!grok deepersearch <query>` | In-depth reasoning |
| `!grok think <query>` | Step-by-step, systematic reasoning |

### Educational Commands (\!):

Educational commands are designed to work in specific channels.

#### 1. Command `!khan <topic>`

  * **Description**: Retrieve lessons or videos from Khan Academy based on the requested topic.
  * **Active Channel**: Only works in the channel with ID `EDUCATIONAL_CHANNEL_ID` (educational channel).
  * **Syntax**: `!khan <topic>`
  * **Example**:
      * Input: `!khan quadratic equation`
      * Output:
        ```
        **Topic: Quadratic equation**
        View lesson/video at: https://www.khanacademy.org/math/algebra/x2f8bb11595b61c86:quadratic-functions-equations
        Source: Khan Academy
        ```
  * **Supported Topics**:
      * `quadratic equation` (quadratic equations)
      * `derivative` (derivatives)
      * `photosynthesis` (photosynthesis)
      * `newton's laws` (Newton's laws)
      * (List will be expanded in the future)
  * **Notes**:
      * If the topic is not found, the bot will prompt to try a different keyword.
      * Example error: `!khan calculus` → "No materials found for this topic. Please try again with a different keyword, e.g., `!khan quadratic equation`."
      * Currently supports a limited set of topics. The topic list will be updated in the future.

#### 2. Command `!math <equation>`

  * **Description**: Solve mathematical equations using the SymPy library (supports equations, derivatives, integrals, etc.).
  * **Active Channel**: Only works in the channel with ID `EDUCATIONAL_CHANNEL_ID` (educational channel).
  * **Syntax**: `!math <equation>`
  * **Example**:
      * Input: `!math x^2 + 5x + 6 = 0`
      * Output:
        ```
        **Equation Solution**
        **Equation**: x^2 + 5x + 6
        **Solutions**: x = -2, x = -3
        Source: SymPy
        ```
      * Input: `!math 2*x + 3`
      * Output:
        ```
        **Equation Solution**
        **Equation**: 2*x + 3
        **Solution**: x = -3/2
        Source: SymPy
        ```
  * **Notes**:
      * Equations must use the variable `x` and standard mathematical syntax (e.g., `x^2` for squared, `*` for multiplication).
      * If the syntax is incorrect, the bot will return an error and suggest: `Error solving equation: <error>. Please use correct syntax, e.g., !math x^2 + 5x + 6 = 0`.
      * Only supports equations with the variable `x` and requires standard syntax. More complex problems (e.g., integrals or systems of equations with multiple variables) will be supported in future versions.

#### 3. Command `!wikipedia <query>`

  * **Description**: Retrieve a summary from Wikipedia for a topic or concept.
  * **Active Channel**: Only works in the channel with ID `WIKI_CHANNEL_ID` (Wikipedia channel).
  * **Syntax**: `!wikipedia <query>`
  * **Example**:
      * Input: `!wikipedia photosynthesis`
      * Output:
        ```
        **Summary: Photosynthesis**
        Photosynthesis is a process used by plants and other organisms to convert light energy into chemical energy that, through cellular respiration, can later be released to fuel the organisms' activities...
        Source: Wikipedia
        ```
  * **Notes**:
      * Queries should be specific for accurate results (e.g., `photosynthesis` instead of `plant`).
      * If no results are found, the bot will notify: `No summary found for this query. Please try again.`
      * Results may be inaccurate if the query is unclear. Use specific keywords.

## Common Errors and Troubleshooting

  * **Command Not Working**:
      * Check if you are using the correct channel (`EDUCATIONAL_CHANNEL_ID` for `!khan` and `!math`, `WIKI_CHANNEL_ID` for `!wikipedia`).
      * Example error: `This command only works in the educational channel.`
  * **Equation Syntax Error**:
      * Ensure correct mathematical syntax, e.g., `x^2 + 5x + 6 = 0` instead of `x squared plus 5x plus 6`.
  * **Materials Not Found**:
      * Check the keyword (e.g., use `quadratic equation` instead of `math` for `!khan`).
      * Try a different or more specific keyword for `!wikipedia`.

## Directory Structure

```
yoombot/
├── data/
│   ├── documents/              # Contains PDF, JSON, and JSONL files for RAG model
│   │   └── mental_counseling/
│   ├── bot.log
│   ├── rag_index/
│   ├── chat_history.db
│   ├── queues.db
│   └── yt_dlp_cache/
├── dist/                       # Generated after building the app
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
│   └── __init__.py
├── main.py
├── config.py
├── database.py
├── logger_gui.py
├── icon.ico
└── .env
```