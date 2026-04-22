import discord
from dotenv import dotenv_values
import os

#
# Mods need the permisson to manage Threads.
#

#---------------------------------------------------------------------------------------------#
#---------------------------------------------------------------------------------------------#

SEND_TICKET_FEEDBACK = True # Set to True to send feedback to users when their ticket is closed

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
CHECK = "<:3654verifiedrainbow:1496592020033241269>"
UNCHECK = "<:39574pridedisapproval:1496592097698910339>"
LOCK_EMOJI = "<:87233lockids:1496591634903732254>"
TRASHCAN_EMOJI = "<:2775applicationdeniedids:1496591571657818112>"
ARCHIVE_EMOJI = "<:51219applicationunderreviewids:1496591555262283856>"
DELETE_EMOJI = "<:2775applicationdeniedids:1496591571657818112>"
TICKET_OPEN_EMOJI = "<:72076mailids:1496591619627946185>"
TRANSCRIPT_EMOJI = "<:32535applicationapprivedids:1496591596504879136>"
REOPEN_EMOJI = "<:85871unlockedids:1496591566565802065>"
INFO_EMOJI = "<:info:1370443515342884936>"
LOADING_EMOJI = "<a:57767rainbowboost:1496592103114018947>"
DANCE_EMOJI = "<a:5332nitro:1496592046109229116>"
LOCK_W_REASON_EMOJI = "<:81496blockedids:1496591628687773898>"

# Button Styles
DANGER = discord.ButtonStyle.danger
SECONDARY = discord.ButtonStyle.secondary
GREEN = discord.ButtonStyle.green
PURPLE = discord.ButtonStyle.blurple

# Embed
EMBED_FOOTER = "❤️ Shizo | by nino161er"

# Base URL for ticket category images (Canstein Berlin collection)
BASE_TICKET_IMAGE_URL = "https://canstein-berlin.de/discord-ticketsystem/"

# Mapping from ticket `Title` strings to image URLs used as embed thumbnails
TICKET_IMAGE_MAP = {
	"Kreativ-Server": BASE_TICKET_IMAGE_URL + "Kreativ-Server.png",
	"Survival (normal)": BASE_TICKET_IMAGE_URL + "Survival-Normal.png",
	"Survival (Skyblock)": BASE_TICKET_IMAGE_URL + "Survival-Skyblock.png",
	"Events": BASE_TICKET_IMAGE_URL + "Event-Server.png",
	"Bug-Report": BASE_TICKET_IMAGE_URL + "Bug-Report.png",
	"Launcher & Mods": BASE_TICKET_IMAGE_URL + "MC-Launcher-und-Mods.png",
	"Server-Beitritt / Bedrock Support": BASE_TICKET_IMAGE_URL + "Server-Beitritt.png",
	"Vor-Ort Treffen und Besuch": BASE_TICKET_IMAGE_URL + "Vor-Ort.png",
	"Discord": BASE_TICKET_IMAGE_URL + "Discord.png",
	"Regelverstoß / Spieler melden": BASE_TICKET_IMAGE_URL + "Regelverto%c3%9f.png",
	"Entbannungsantrag": BASE_TICKET_IMAGE_URL + "Entbannungsantrag.png",
	"Kooperationen": BASE_TICKET_IMAGE_URL + "Kooperationen.png",
	"Bewerbung": BASE_TICKET_IMAGE_URL + "Bewerbung.png",
	"Account gehackt / neuer Account": BASE_TICKET_IMAGE_URL + "Account-gehackt.png",
	"Sonstiges": BASE_TICKET_IMAGE_URL + "Sonstiges.png",
}