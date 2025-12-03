# ruff: noqa: F403 F405
import discord
from discord.ui import Modal, TextInput
from util.constants import *
from util.tickets.transcript import *
from typing import TYPE_CHECKING
from lang.texts import *

if TYPE_CHECKING:
    from cogs.tickets import TicketCog

# Rename the ticket, before it gets archived
class ThreadModalRename(Modal):
    def __init__(self):
        super().__init__(title=ARCHIVE_TICKET_MODAL_TITLE)
        self.name_TextInput = TextInput(
            label=RENAME_TICKET_LABEL,
            placeholder=RENAME_TICKET_PLACEHOLDER,
            max_length=30,
            required=False
        )
        self.add_item(self.name_TextInput)

    async def on_submit(self, interaction: discord.Interaction):
        new_name = self.name_TextInput.value
        try:
            await interaction.response.defer()
            await interaction.channel.edit(name=new_name, archived=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(ARCHIVE_ERROR.format(error=e), ephemeral=True)

# Get a summary of the ticket after transcripting it
class TransDesc(Modal):
    def __init__(self, bot):
        super().__init__(title=TICKET_DESCRIPTION_MODAL_TITLE)
        self.bot = bot
        self.name_TextInput = TextInput(
            label=TICKET_DESCRIPTION_LABEL,
            placeholder="",
            required=False,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.name_TextInput)

    async def on_submit(self, interaction: discord.Interaction):
        summary = self.name_TextInput.value
        try:
            await trans_ticket(interaction=interaction, summary=summary, bot=self.bot)
            
        except discord.HTTPException as e:
            await interaction.response.send_message(DESCRIPTION_ERROR.format(error=e), ephemeral=True)
            pass

# Get a reason to close the ticket
class closeThreadReasonModal(Modal):
    def __init__(self, ticketcog: "TicketCog"):
        super().__init__(title=CLOSE_TICKET_MODAL_TITLE)
        self.ticketcog = ticketcog
        self.reason_TextInput = TextInput(
            label=CLOSE_REASON_LABEL,
            placeholder=CLOSE_REASON_PLACEHOLDER,
            style=discord.TextStyle.long,
            max_length=300
        )
        self.add_item(self.reason_TextInput)
        
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        reason = self.reason_TextInput.value
        await self.ticketcog.close_thread_with_reason(interaction=interaction, reason=reason)

# Area saving modal, to get the world and coordinates
class bereichModal(Modal):
    def __init__(self, ticketcog: "TicketCog"):
        super().__init__(title=AREA_SAVING_MODAL_TITLE)
        self.ticketcog = ticketcog
        self.welt = discord.ui.TextInput(
            label=WORLD_LABEL,
            placeholder=WORLD_PLACEHOLDER,
            style=discord.TextStyle.short,
            max_length=60
        )
        self.koordinaten = discord.ui.TextInput(
            label=COORDINATES_LABEL,
            placeholder=COORDINATES_PLACEHOLDER
        )

        self.add_item(self.welt)
        self.add_item(self.koordinaten)
        
    async def on_submit(self, interaction: discord.Interaction):
        fields = {
            "Title": AREA_SAVING_TITLE,
            "Koordinaten": self.koordinaten.value,
            "Welt": self.welt.value,
            "message": DEFAULT_HELP_MESSAGE
        }
        print(f"ticketcog type: {type(self.ticketcog)}")
        print(f"Has create_ticket_thread: {hasattr(self.ticketcog, 'create_ticket_thread')}")
        await self.ticketcog.create_ticket_thread(interaction=interaction, fields=fields)

# Get the coordinates of the plot
class parzelleModal(Modal):
    def __init__(self, ticketcog: "TicketCog"):
        super().__init__(title=PLOT_TRANSFER_MODAL_TITLE)
        self.ticketcog = ticketcog
        
        self.ingame_name = discord.ui.TextInput(
            label=INGAME_NAME_LABEL,
            placeholder=INGAME_NAME_PLACEHOLDER,
            style=discord.TextStyle.short,
            max_length=60
        )
        self.canstein_name = discord.ui.TextInput(
            label=CANSTEIN_NAME_LABEL,
            placeholder=CANSTEIN_NAME_PLACEHOLDER,
            style=discord.TextStyle.short,
            max_length=60,
            required=False
        )
        self.add_item(self.ingame_name)
        self.add_item(self.canstein_name)

    async def on_submit(self, interaction: discord.Interaction):
        fields = {
            "Title": PLOT_TRANSFER_TITLE,
            "Ingame Name": self.ingame_name.value,
            "Canstein Name": self.canstein_name.value,
            "message": DEFAULT_HELP_MESSAGE
        }
        await self.ticketcog.create_ticket_thread(interaction=interaction, fields=fields)