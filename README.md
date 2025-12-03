# Shizo Discord Bot
A feature‑rich Discord bot built with Python and `discord.py`, offering:

- 🎵 Advanced music system (YouTube + radio)
- 🎫 Ticket system with threads, transcripts, and mod tools
- 🔧 GitHub integration
- 🎮 Fun mini‑games and utilities

---

## Features

### 🎵 Music System

- Play songs from YouTube URLs or search terms
- Queue management (add, view, shuffle, clear, auto‑play)
- YouTube Music “chart” / trending integration
- Random “Inspire Me” song picker with rich now‑playing embeds
- Per‑guild music queues with duration formatting
- Uses `yt-dlp` + FFmpeg with tuned options in `util.constants.YT_OPTS`

Main implementation: `cogs.music.MusicCog`

Core helpers:

- `MusicCog.make_embed`
- `MusicCog.play_next`
- `MusicCog.create_now_playing_embed`
- `MusicCog.update_progress`
- `util.music.queue`

### 📻 Radio

- Play internet radio streams from URLs or pre‑defined stations
- Support for `.m3u`, `.pls`, `.asx`, `.xspf` playlist formats
- Rich “Radio Stream Started” embed with listener count

Core implementation: `cogs.radio.RadioCog`, especially:

- `RadioCog._parse_playlist_file`
- `RadioCog._create_radio_embed`

### 🎫 Ticket System

- Slash command `/tickets` for server‑wide ticket setup
- Category selection via dropdown (Discord, Minecraft, Bereich sichern, Parzelle, Entbannung, Sonstiges)
- Ticket creation in private threads with dynamic fields and emojis
- Close / delete / archive / reopen flows
- Full HTML transcripts with multiple themes (Dark, Teal, Lyntr, Hackerman, Text)
- Stores ticket <-> user relations in JSON

Main components:

- Cog: `cogs.tickets.TicketCog`
- Views / UI: `views.ticketviews.ActionsView`, `views.ticketviews.TicketSetupView`, `views.ticketviews.TicketDropdown`
- Modals: `modals.ticketmodals`
  - `TransDesc` (transcript description)
  - `bereichModal` (area saving)
  - `parzelleModal` (plot transfer)
- Ticket utilities:  
  - `util.tickets.ticket_creator` (JSON storage)
  - `util.tickets.transcript.trans_ticket` (HTML export)
  - Template: `util/transcript_template.html`

All user‑facing texts are centralized in `lang.texts.TEXTS` for easy localization.

### 🔧 GitHub Integration

Slash command `/github`:

- Shows repository links, releases, and a call to star the repo
- Uses `EMBED_FOOTER` and shared styles from `util.constants`

Implementation: `cogs.github.GithubCog`

### 🎮 Games & Fun

- **ASCII Art**: `/art` command returns random ASCII art from `util.games.ascii_arts` via `cogs.art.ArtCog`
- **Counting Game**: `cogs.counting.CountingCog` manages a counting channel with chance to fail using `counting.random_fail_message`
- **Guess the Number**: `cogs.guess_the_number.GuessNumberCog` with temperature emojis via `GuessNumberCog.get_temperature_emoji`

---

## Tech Stack

- **Language:** Python 3.9+
- **Discord Library:** `discord.py`
- **YouTube / Audio:** `yt-dlp` + FFmpeg
- **Env & Config:** .env + `util.constants`
- **Templating:** `jinja2` + HTML (transcripts)
- **Logging:** `logging` + `colorlog`

See requirements.txt for full dependency list.

---

## File Structure

```bash
.
├── .env                       # Environment variables (not committed)
├── README.md                  # Project documentation
├── requirements.txt           # Python dependencies
├── config/
│   └── tickets.json           # Persistent ticket data
└── src/
    ├── main.py                # Bot entry point
    ├── cogs/
    │   ├── art.py             # /art ASCII art command
    │   ├── counting.py        # Counting game
    │   ├── github.py          # /github command
    │   ├── guess_the_number.py# Guess the number game
    │   ├── music.py           # Music system (queues, charts, history)
    │   ├── radio.py           # Internet radio player
    │   └── tickets.py         # Ticket system core
    ├── lang/
    │   └── texts.py           # Localized text constants
    ├── modals/
    │   ├── embeds.py          # Simple embed helper
    │   └── ticketmodals.py    # Ticket & transcript modals
    ├── util/
    │   ├── constants.py       # Config, emojis, YT_OPTS, etc.
    │   ├── transcript_template.html # HTML transcript theme
    │   ├── games/
    │   │   └── ascii_arts.py  # ASCII art collection + getter
    │   ├── music/
    │   │   └── queue.py       # Music queue abstraction
    │   └── tickets/
    │       ├── ticket_creator.py # Ticket storage helpers
    │       └── transcript.py  # Transcript generator
    └── views/
        └── ticketviews.py     # Ticket and music UI Views
```

---

## Installation

### Prerequisites

- Python $3.8$ or higher
- FFmpeg installed and available in `$PATH$
- A Discord bot application and token

### 1. Clone the Repository

```bash
git clone https://github.com/ninocss/Shizo.git
cd Shizo
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create `.env`

Create a `.env` file in the project root (same folder as `src/`):

```env
# The Bot token
DISCORD_TOKEN=your_bot_token_here

# Guild ID where slash commands are synced
SERVER=your_server_id_here

# Music interaction channel (e.g. #music)
I_CHANNEL=your_music_channel_id_here

# Transcript log channel
TRANS_CHANNEL=your_transcript_channel_id_here

# Role names
MOD=Mod
TRAIL_MOD=Trail_mod

# Ticket creation channel ID
TICKET_CHANNEL_ID=your_ticket_channel_id_here

# Optional: role IDs, additional config...
TEAM_ROLE=Support
```

The `.env` is loaded by [`util.constants`](src/util/constants.py).

### 4. Run the Bot

From the project root:

```bash
python -m src.main
```

Or:

```bash
python main.py
```

On first run, Discord may take a short time to register slash commands.

---

## Configuration

Many core options live in [`util.constants`](src/util/constants.py):

- Ticket file path: `TICKET_CREATOR_FILE = "config/tickets.json"`
- Emojis: `CHECK`, `UNCHECK`, `LOCK_EMOJI`, `TRANSCRIPT_EMOJI`, etc.
- YT‑DLP options: [`YT_OPTS`](src/util/constants.py)
- Embed footer: `EMBED_FOOTER = "❤️ Shizo | by nino.css"`
- Feature toggles:
  - `SEND_TICKET_FEEDBACK`
  - `SET_VC_STATUS_TO_MUSIC_PLAYING`
  - `AUTO_PLAY_ENABLED`

Texts for tickets and UI are in [`lang.texts.TEXTS`](src/lang/texts.py). Edit there to change languages or phrasing.

---

## Commands (Overview)

### Music

Implemented in [`cogs.music.MusicCog`](src/cogs/music.py):

- `/play <query>` – play from URL or search term
- `/queue` – show current queue
- `/shuffle` – shuffle queue with summary
- `/clearqueue` – vote to clear the queue
- `/stop` – stop music and disconnect
- `/chart` – play random song from YouTube Music charts
- “Inspire Me”, “Most Played”, “Charts”, “History” buttons via [`ActionsView`](src/views/ticketviews.py)

### Tickets

Implemented in [`cogs.tickets.TicketCog`](src/cogs/tickets.py):

- `/tickets` – send ticket setup embed (Admin only)
- `/close` – close a ticket thread
- `/menu` – mod management menu (buttons)
- Transcript modal via [`TransDesc`](src/modals/ticketmodals.py)

### Misc

- `/github` – info about the GitHub repo ([`GithubCog`](src/cogs/github.py))
- `/art` – random ASCII art ([`ArtCog`](src/cogs/art.py))
- Counting & number guessing commands in:
  - [`CountingCog`](src/cogs/counting.py)
  - [`GuessNumberCog`](src/cogs/guess_the_number.py)

---

## Logging & Debugging

Logging is configured in [`main.setup_logging`](src/main.py) using `colorlog`:

- Logs command registration, guild sync, and errors
- Ticket system has extra logging in [`cogs.tickets`](src/cogs/tickets.py)

If **slash commands don’t appear**:

1. Verify `DISCORD_TOKEN` and `SERVER` in `.env`
2. Check bot has `applications.commands` scope
3. Look at console output for sync logs from [`Bot.setup_hook`](src/main.py)

---

## Security

- Do **not** commit `.env` or any file containing your bot token.
- Make sure `.env` is in `.gitignore`.
- Limit bot permissions to what’s needed (manage threads, read/send messages, connect/speak, embed links, attach files, use slash commands).

---

## Credits

Created by **nino**

- Bot framework: `discord.py`
- Music: `yt-dlp`
- Audio: FFmpeg
- Transcripts: custom HTML in [`util/transcript_template.html`](src/util/transcript_template.html)

If you like the bot, consider starring the repository and sharing feedback via the `/github` command.On first run, Discord may take a short time to register slash commands.