# Shizo Discord Bot

A feature-rich Discord bot built with Python and discord.py, offering music playback, ticket system, GitHub integration, and entertainment features.

## Features

### 🎵 Music System
- Play music from YouTube URLs or search terms
- Queue management with shuffle functionality
- Skip songs and view current queue
- Support for playlists
- High-quality audio streaming with FFmpeg

### 🎫 Ticket System
- Create private support tickets
- Automated ticket management
- Role-based access control
- Ticket closing with reason logging
- Auto-archive after timeout

### 🔧 GitHub Integration
- GitHub repository interactions
- Webhook support for repository events
- Issue and pull request notifications

### 📻 Radio
- Internet radio streaming capabilities
- Multiple radio station support

### 🎮 Entertainment
- Counting game
- Guess the number game
- Interactive games with leaderboards

## Installation

### Prerequisites
- Python 3.8 or higher
- FFmpeg (for audio processing)
- A Discord bot token

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/ninocss/Shizo/
cd Shizo
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Install FFmpeg**
   - **Windows**: Download from [FFmpeg official site](https://ffmpeg.org/download.html)
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian) or `sudo yum install ffmpeg` (CentOS/RHEL)

4. **Configure the bot**
   - Create a `constants.py` file with your configuration:
```python
# YouTube-DL Options
YT_OPTS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

# Emojis
LOADING_EMOJI = "⏳"
INFO_EMOJI = "ℹ️"
CHECK = "✅"
UNCHECK = "❌"
```
   - Create a `.env` file with this config:

   ```env
   # Channels are always the channel ID. Role Names just as the name of the role, everything without ""

   # The Bot token
   DISCORD_TOKEN=your_bot_token_here

   # The Server, the bot will sync its commands to
   SERVER=your_server_id_here

   # The interaction channel for music (#music or #musik)
   I_CHANNEL=your_music_channel_id_here

   # The transcript channel
   TRANS_CHANNEL=your_transcript_channel_id_here

   # Mod role name
   MOD=Mod

   # Trail mod role name
   TRAIL_MOD=Trail_mod

   # The channel where you can create tickets
   TICKET_CHANNEL_ID=your_ticket_channel_id_here
   ```

5. **Run the bot**
```bash
python src/main.py
```

## Commands

### Music Commands
- `/play <song>` - Play music from YouTube URL or search term
- `/skip` - Skip the current song
- `/queue` - Display the current queue
- `/shuffle` - Shuffle the queue
- `/stop` - Stop music and disconnect from voice channel

### Ticket Commands
- `/tickets` - Set up the ticket system (Admin only)
- `/close` - Close a ticket (use in ticket threads)
- `/menu` - Gives mods a useful management menu (Mods only)

### Other Commands
- `/github` - GitHub-related commands
- Various entertainment commands for games

## Configuration

### Required Permissions
The bot needs the following permissions in your Discord server:
- Read Messages
- Send Messages
- Connect to Voice Channels
- Speak in Voice Channels
- Manage Threads
- Create Private Threads
- Embed Links
- Attach Files
- Use Slash Commands

## File Structure
```bash
src/
├── main.py                 # Main bot file
├── constants.py            # Configuration constants
├── .env                    # Your .env
├── cogs/
│   ├── art.py              # Just the file with ASCII art
│   ├── music.py            # Music functionality
│   ├── tickets.py          # Ticket system
│   ├── github.py           # GitHub integration
│   ├── radio.py            # Radio features
│   ├── counting.py         # Counting game
│   └── guess_the_number.py # Number guessing game
├── views/
│   └── ticketviews.py      # Ticket UI components
├── modals/
│   └── ticketmodals.py     # Ticket forms
├── util/
│   ├── ascii_arts.py       # Helping with arts
│   ├── queue.py            # Music queue management
│   ├── play_next.py        # Music playback logic
│   └── ticket_creator.py   # Ticket creation utilities
├── embeds.py               # Discord embed templates
└── texts.py                # Text constants
```

## Dependencies
- `discord.py` - Discord API wrapper
- `yt-dlp` - YouTube downloader
- `colorlog` - Colored logging
- `asyncio` - Asynchronous programming
- `concurrent.futures` - Thread pool execution

## Troubleshooting

### Common Issues

**Bot not responding to commands:**
- Check if the bot has proper permissions
- Verify the bot token is correct
- Ensure slash commands are synced

**Music not playing:**
- Verify FFmpeg is installed and in PATH
- Check if the bot has voice channel permissions
- Ensure you're in the same voice channel as the bot

**Tickets not working:**
- Verify channel IDs in `constants.py`
- Check if required roles exist
- Ensure the bot has thread management permissions

### Logging
The bot uses colored logging for better debugging. Check the console output for detailed information about bot operations and any errors.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation in the code comments

## Credits

Created by nino
- Website: www.ninoio.gay / www.ninoio.xyz
- Bot Framework: discord.py
- Music: yt-dlp
- Audio Processing: FFmpeg

---

**Note**: Make sure to keep your bot token secure and never share it publicly. Add `.env` and `constants.py` to your `.gitignore` file to prevent accidental commits of sensitive information.
