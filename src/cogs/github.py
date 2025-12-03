# ruff: noqa: F403 F405
import discord
from discord.ext import commands
from discord import app_commands
from util.constants import *
from views.ticketviews import *
from modals.ticketmodals import *
from util.tickets.ticket_creator import *
from lang.texts import *

class GithubCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # The /github command
    @app_commands.command(name="github", description="Show information about the bot's GitHub repository")
    async def github(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="GitHub Repository",
            description=(
                "Here you can find the source code, report issues, and contribute to the bot!\n\n"
                "[View Repository](https://github.com/ninocss/Shizo)\n"
                "[Report an Issue](https://github.com/ninocss/Shizo/issues)\n"
                "[Contribute](https://github.com/ninocss/Shizo/pulls)\n"
            ),
            color=0x00ff00
        )
        embed.set_author(
            name="GitHub",
            icon_url=interaction.client.user.avatar.url if interaction.client.user.avatar else None
        )
        embed.set_footer(text=EMBED_FOOTER)
        embed.set_thumbnail(url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png")
        
        embed.add_field(
            name="Latest Release",
            value="[Releases](https://github.com/ninocss/Shizo/releases)",
            inline=True
        )
        embed.add_field(
            name="Stars",
            value="⭐ Give me a star if you like the bot!",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    async def cog_load(self):
        self.bot.tree.add_command(self.github, guild=discord.Object(id=SYNC_SERVER))