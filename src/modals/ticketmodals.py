# ruff: noqa: F403 F405
import discord
from discord.ui import Modal, TextInput
from util.constants import *
from util.tickets.transcript import *
from typing import TYPE_CHECKING
from lang.texts import *

if TYPE_CHECKING:
    from cogs.tickets import TicketCog

# Rename the ticket before it gets archived
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


class RenameThreadModal(Modal):
    """Modal to rename a ticket/thread without archiving it."""
    def __init__(self):
        super().__init__(title="Ticket umbenennen")
        self.name_TextInput = TextInput(
            label=RENAME_TICKET_LABEL,
            placeholder=RENAME_TICKET_PLACEHOLDER,
            max_length=100,
            required=True
        )
        self.add_item(self.name_TextInput)

    async def on_submit(self, interaction: discord.Interaction):
        new_name = (self.name_TextInput.value or "").strip()
        if not new_name:
            try:
                await interaction.response.send_message("Bitte gib einen gültigen Namen an.", ephemeral=True)
            except Exception:
                pass
            return

        # permission check: only supporters or admins may rename
        try:
            if not (interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.kick_members):
                await interaction.response.send_message(embed=discord.Embed(title=NO_PERMISSION_TITLE, description=NO_PERMISSION, color=0xff0000), ephemeral=True)
                return
        except Exception:
            # best-effort: continue
            pass

        try:
            await interaction.response.defer()
            await interaction.channel.edit(name=new_name)
            await interaction.followup.send(f"✅ Ticket umbenannt in: **{new_name}**", ephemeral=True)
        except Exception as e:
            try:
                await interaction.followup.send(f"Fehler beim Umbenennen: {e}", ephemeral=True)
            except Exception:
                pass

# Get a summary of the ticket after transcribing it
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