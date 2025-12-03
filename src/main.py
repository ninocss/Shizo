# ruff: noqa: F403 F405
import asyncio
import logging

import colorlog
import discord
from discord import Intents
from discord.ext import commands

from util.constants import *
from views.ticketviews import *
from cogs.tickets import TicketCog
from cogs.github import GithubCog
from cogs.music import MusicCog
from cogs.radio import RadioCog
from cogs.counting import CountingCog
from cogs.guess_the_number import GuessNumberCog
from cogs.art import ArtCog

# Setup colored logging
def setup_logging() -> logging.Logger:
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(name_log_color)s%(name)s%(reset)s: [%(levelname)s] %(message_log_color)s%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'cyan',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={
            'message': {level: 'white' for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']},
            'name': {level: 'light_black' for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']}
        }
    ))
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    return logging.getLogger(__name__)

logger = setup_logging()

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        intents = Intents.default()
        intents.message_content = True
        intents.typing = True
        intents.presences = True
        intents.members = True
        intents.voice_states = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            activity=discord.Activity(name="/github • /art", type=discord.ActivityType.competing),
            *args, **kwargs
        )

    async def setup_hook(self):
        # Add cogs
        cogs = [
            TicketCog(self),
            GithubCog(self),
            #MusicCog(self),
            #RadioCog(self),
            CountingCog(self),
            GuessNumberCog(self),
            #ArtCog(self)
        ]
        
        for cog in cogs:
            await self.add_cog(cog)
        
        # Add persistent views
        ticket_cog = self.get_cog('TicketCog')
        views = [
            TicketSetupView(ticketcog=ticket_cog),
            PersistentCloseView(bot=self, ticketcog=ticket_cog),
            CloseThreadView(bot=self, ticketcog=ticket_cog),
            ActionsView(bot=self)
        ]
        
        for view in views:
            self.add_view(view)

        # Sync commands
        guild_id = discord.Object(id=SYNC_SERVER)
        synced = await self.tree.sync(guild=guild_id)
        cmd_names = [cmd.name for cmd in synced]
        logger.info(f"🔄 COMMAND SYNC COMPLETE 🔄")
        logger.info(f"📊 Total Commands: {len(cmd_names)}")
        logger.info(f"📋 Commands: {', '.join(cmd_names)}")
        logger.info(f"🎯 Guild: {SYNC_SERVER}")
            
    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"---------------------------------------------------")
        
        try:
            music_cog = self.get_cog('MusicCog')
            if music_cog:
                await music_cog.send_static_message()
                logger.info("Sent static music embed.")
        except Exception as e:
            logger.error(f"Error sending static music embed: {e}")

async def main():
    bot = Bot()
    await bot.start(TOKEN)
    
if __name__ == "__main__":
    asyncio.run(main())


