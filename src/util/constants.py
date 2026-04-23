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
_config = dotenv_values(_config_path)

TICKET_CHANNEL_ID = _config.get("TICKET_CHANNEL_ID")
TOKEN = _config.get('DISCORD_TOKEN')
SYNC_SERVER = _config.get('SERVER')
TRANS_CHANNEL_ID = _config.get('TRANS_CHANNEL')
TEAM_ROLE = _config.get('TEAM_ROLE')
MOD = _config.get('MOD')
TRAIL_MOD = _config.get('TRAIL_MOD')
TICKET_CREATOR_FILE = "config/tickets.json"
TEAM_ROLE = _config.get('TEAM')

# Emojis for the bot
CHECK = "<:Yes:1496860724561969375>"

UNCHECK = "<:No:1496860726256472276>"

LOCK_EMOJI = "<:Lock:1496860721441673407>"

TRASHCAN_EMOJI = "<:Trashcan:1496860729796464760>"

ARCHIVE_EMOJI = "<:Archive:1496860727636525116>"

DELETE_EMOJI = "<:Trashcan:1496860729796464760>"

TICKET_OPEN_EMOJI = "<:Mail:1496860731520450610>"

TRANSCRIPT_EMOJI = "<:Trans:1496862379911282799>"

REOPEN_EMOJI = "<:Unlock:1496860723345887302>"

INFO_EMOJI = "<:Info:1496860733374464011>"

LOADING_EMOJI = "<a:57767rainbowboost:1496592103114018947>"

LOCK_W_REASON_EMOJI = "<:Lock_with_reason:1496860719658958868>"

# Button Styles
DANGER = discord.ButtonStyle.danger
SECONDARY = discord.ButtonStyle.secondary
GREEN = discord.ButtonStyle.green
PURPLE = discord.ButtonStyle.blurple

# Embed
EMBED_FOOTER = "❤️ Tickets | by nino161er"

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