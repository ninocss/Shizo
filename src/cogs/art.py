# ruff: noqa: F403 F405
from discord.ext import commands
from util.constants import *
from discord import *
from discord.ui import View, Button

from util.games.ascii_arts import get_ascii_art

class ArtCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def next_call(self, interaction: discord.Interaction):
        art = get_ascii_art()
        
        async def send_call(interaction: discord.Interaction):
            await interaction.response.defer()
            user = interaction.user
            await user.send(f"Here is your Ascii art!! ```ansi\n{art}\n```")
        
        next_btn = Button(style=GREEN, label="Next", emoji="➡️")
        send_btn = Button(style=SECONDARY, label="Send it to me", emoji="📨")
        
        next_btn.callback = self.next_call
        send_btn.callback = send_call
        
        view = View(timeout=180)
        view.add_item(next_btn)
        view.add_item(send_btn)
        
        await interaction.response.send_message(f"```ansi\n{art}\n```", ephemeral=True, delete_after=180, view=view)
        
    @app_commands.command(name="art", description="gives you ASCII art :)")     
    async def art(self, interaction: discord.Interaction):
        art = get_ascii_art()
        
        async def send_call(interaction: discord.Interaction):
            await interaction.response.defer()
            user = interaction.user
            await user.send(f"Here is your Ascii art!! ```ansi\n{art}\n```")
        
        next_btn = Button(style=GREEN, label="Next", emoji="➡️")
        send_btn = Button(style=SECONDARY, label="Send it to me", emoji="📨")
        
        next_btn.callback = self.next_call
        send_btn.callback = send_call
        
        view = View(timeout=180)
        view.add_item(next_btn)
        view.add_item(send_btn)
        
        await interaction.response.send_message(f"```ansi\n{art}\n```", ephemeral=True, delete_after=180, view=view)

    async def cog_load(self):
        self.bot.tree.add_command(self.art, guild=discord.Object(id=SYNC_SERVER))
