import discord
from dotenv import dotenv_values
import os

#
# Mods need the permisson to manage Threads.
#

#---------------------------------------------------------------------------------------------#
#---------------------------------------------------------------------------------------------#

SEND_TICKET_FEEDBACK = True # Set to True to send feedback to users when their ticket is closed

SET_VC_STATUS_TO_MUSIC_PLAYING = True # Set to True, if the bot should change the VC status

AUTO_PLAY_ENABLED = True  # Set to True to enable autoplay feature in MusicCog (BETA)

#---------------------------------------------------------------------------------------------#
#---------------------------------------------------------------------------------------------#

# Load config stuff
_config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
print("Looking for .env at:", _config_path)
print("Exists:", os.path.exists(_config_path))

_config = dotenv_values(_config_path)
TICKET_CHANNEL_ID = _config.get("TICKET_CHANNEL_ID")
TOKEN = _config.get('DISCORD_TOKEN')
SYNC_SERVER = _config.get('SERVER')
I_CHANNEL = _config.get('I_CHANNEL')
TRANS_CHANNEL_ID = _config.get('TRANS_CHANNEL')
TEAM_ROLE = _config.get('TEAM_ROLE')
MOD = _config.get('MOD')
TRAIL_MOD = _config.get('TRAIL_MOD')
TICKET_CREATOR_FILE = "config/tickets.json"

# Emojis for the bot
CHECK = "<:check:1368203772123283506>"
UNCHECK = "<:X_:1373405777297014944>"
LOCK_EMOJI = "<:lock:1368203397467082823>"
TRASHCAN_EMOJI = "<:bin:1368203374092353627>"
ARCHIVE_EMOJI = "<:save:1368203337337540648>"
DELETE_EMOJI = "<:bin:1368203374092353627>"
TICKET_OPEN_EMOJI = "<:creation:1368203348066439190>"
TRANSCRIPT_EMOJI = "<:transcript:1368207338162491513>"
REOPEN_EMOJI = "<:unlock:1368203388231094373>"
INFO_EMOJI = "<:info:1370443515342884936>"
LOADING_EMOJI = "<a:2923printsdark:1367119727763259533>"
DANCE_EMOJI = "<a:dance:1369716119073587290>"
LOCK_W_REASON_EMOJI = "<:lock_with_reason:1371107805867671643>"

# Button Styles
DANGER = discord.ButtonStyle.danger
SECONDARY = discord.ButtonStyle.secondary
GREEN = discord.ButtonStyle.green
PURPLE = discord.ButtonStyle.blurple

# YT_OPTS
YT_OPTS = {
    'format': 'bestaudio/best',
    'default_search': 'auto',
    'noplaylist': False,
    'quiet': False,
    'no_warnings': False,
    'cachedir': False,
    'restrictfilenames': True,
    'source_address': '0.0.0.0',
    'socket_timeout': 15,
    'retries': 5,
    'fragment_retries': 5,
    'skip_unavailable_fragments': True,
    'geo_bypass': True,
    'include_thumbnail': True,
    'outtmpl': '-',
    'prefer_ffmpeg': True,
    'postprocessors': [
        {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'opus',
            'preferredquality': '128',
        },
        {'key': 'FFmpegMetadata'},
    ],
}

# Embed
EMBED_FOOTER = "❤️ Shizo | by nino.css"