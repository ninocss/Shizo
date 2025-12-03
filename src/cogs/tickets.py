# ruff: noqa: F403 F405
import discord
from discord.ext import commands
from discord import app_commands
from util.constants import *
from views.ticketviews import *
from modals.ticketmodals import *
from util.tickets.ticket_creator import *
import traceback
from lang.texts import *
import logging
import colorlog
from modals.embeds import simple_embed

if TYPE_CHECKING:
    from cogs.tickets import TicketCog

# Setup colored logging
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
        'message': {
            'DEBUG': 'white',
            'INFO': 'white',
            'WARNING': 'white',
            'ERROR': 'white',
            'CRITICAL': 'white',
        },
        'name': {
            'DEBUG': 'light_black',
            'INFO': 'light_black',
            'WARNING': 'light_black',
            'ERROR': 'light_black',
            'CRITICAL': 'light_black',
        }
    }
))
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)

class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("TicketCog initialized.")

    @app_commands.command(name="tickets", description="Setup tickets in this channel!")
    async def setup(self, interaction: discord.Interaction):
        logger.info(f"Setup command invoked by {interaction.user} in channel {interaction.channel}.")
        if not interaction.user.guild_permissions.administrator:
            logger.warning(f"User {interaction.user} tried to use setup without permission.")
            embed = simple_embed(NO_PERMISSION, color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = simple_embed(EMBED_CREATED, color=0x00ff00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        embed = discord.Embed(
            title=f"{SUPPORT_HEADER_TEXT}",
            description=f"📋 {TICKET_CREATION_EMBED_TEXT}",
            color=0x5865F2
        )
        embed.set_author(
            name=f"{BOT_NAME}", 
            icon_url=interaction.client.user.avatar.url if interaction.client.user.avatar else None
        )

        embed.add_field(
            name=f"{WHAT_NEXT}", 
            value=f"{WHAT_NEXT_VALUE}", 
            inline=False
        )
        embed.set_footer(
            text=f"{EMBED_FOOTER}",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )

        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.channel.send(embed=embed, view=TicketSetupView(self))
        logger.info(f"Ticket setup embed sent by {interaction.user} in channel {interaction.channel}.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.author.guild_permissions.kick_members:
            return
        if not message.content.lower().startswith("?close") and not message.content.lower().startswith("?c"):
            return

        if not isinstance(message.channel, discord.Thread):
            logger.warning("Close command used outside of a thread.")
            embed = simple_embed(CAN_ONLY_BE_USED_IN_THREAD, color=0xff0000)
            await message.channel.send(embed=embed, ephemeral=True)
            return
        
        if message.channel.parent_id != int(TICKET_CHANNEL_ID):
            logger.warning("Close command used in a thread not under the ticket channel.")
            embed = simple_embed(CAN_ONLY_BE_USED_IN_THREAD, color=0xff0000)
            await message.channel.send(embed=embed, ephemeral=True)
            return
        
        cancel_btn = Button(emoji=UNCHECK, label=CANCEL_BUTTON_LABEL, style=SECONDARY)
        cancel_btn.callback = self.cancel_btn_callback

        view = PersistentCloseView(ticketcog=self, bot=self.bot)
        view.add_item(cancel_btn)
        
        ticket_creator = get_ticket_creator(message.channel.id)

        await message.channel.send(view=view, content=f"{TICKET_CLOSE_PROMPT}".format(ticket_creator=ticket_creator))

    async def cancel_btn_callback(self, interaction):
        logger.info(f"Cancel button clicked by {interaction.user} in message {interaction.message.id}.")
        await interaction.message.delete()

    async def close_thread_confirmation(self, interaction: discord.Interaction):
        logger.info(f"Close thread confirmation requested by {interaction.user} in thread {interaction.channel}.")
        embed = simple_embed(TICKET_CLOSE_CONFIRMATION.format(user=interaction.user.mention), color=0xffaa00)
        await interaction.response.send_message(embed=embed, view=CloseConfirmView(ticketcog=self), ephemeral=False)

    async def close_thread_with_reason(self, interaction: discord.Interaction, reason: str):
        logger.info(f"Close thread with reason '{reason}' requested by {interaction.user} in thread {interaction.channel}.")
        embed = simple_embed(TICKET_CLOSE_WITH_REASON_CONFIRMATION.format(user=interaction.user.mention, reason=reason), color=0xffaa00)
        await interaction.followup.send(embed=embed, view=CloseReasonConfirmView(ticketcog=self, bot=self.bot, reason=reason), ephemeral=False)

    async def create_ticket_thread(self, interaction: discord.Interaction, fields: dict):
        global TICKET_CREATOR
        guild = interaction.guild
        support_role = discord.utils.get(guild.roles, name=MOD)
        supporthilfe_role = discord.utils.get(guild.roles, name=TRAIL_MOD)

        try:
            title = fields.get("Title")
            logger.info(f"Creating ticket thread '{title}' for user {interaction.user} in channel {interaction.channel}.")
            thread = await interaction.channel.create_thread(name=title + f" von {interaction.user.display_name}", type=discord.ChannelType.private_thread)

            save_ticket_creator(thread.id, interaction.user.id)
            TICKET_CREATOR = interaction.user

            await thread.add_user(interaction.user)
            await thread.edit(invitable=False)

            embed = discord.Embed(
                title=f"{TICKET_OVERVIEW_TITLE}",
                description=f"{CLOSE_EMBED_DESC}",
                color=0x00D166
            )
            embed.set_footer(
                text=f"{EMBED_FOOTER}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            embed.set_author(
                name=f"{interaction.user.name}", 
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )

            for name, value in fields.items():
                if name not in ["Title", "Rolle", "message"] and value.strip():
                    emoji = "📝"
                    if "email" in name.lower():
                        emoji = "📧"
                    elif "problem" in name.lower() or "issue" in name.lower():
                        emoji = "❗"
                    elif "description" in name.lower():
                        emoji = "📋"
                    elif "priority" in name.lower():
                        emoji = "🚨"
                    
                    embed.add_field(name=f"{emoji} {name}", value=f"```{value}```", inline=False)

            message = fields.get("message", DEFAULT_HELP_MESSAGE)
            
            await thread.send(
                embed=embed,
                view=PersistentCloseView(bot=self.bot, ticketcog=self),
                content=f"{support_role.mention if support_role else ''} {supporthilfe_role.mention if supporthilfe_role else ''} {message}"
            )
            
            success_embed = simple_embed(TICKET_CREATION_SUCCESS.format(thread=thread.mention), color=0x00ff00)
            await interaction.response.send_message(embed=success_embed, ephemeral=True, delete_after=20)
            logger.info(f"Ticket thread '{thread.name}' created for user {interaction.user}.")

        except Exception as e:
            logger.error(f"Error creating ticket thread for user {interaction.user}: {e}")
            error_embed = simple_embed(TICKET_CREATION_ERROR, color=0xff0000)
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=10)
            print(f"Fehler beim Erstellen des Tickets: {e}")
            print(traceback.format_exc())

    @app_commands.command(name="menu", description="Manage the current ticket thread")
    async def menu(self, interaction: discord.Interaction):
        logger.info(f"Menu command invoked by {interaction.user} in channel {interaction.channel}.")
        
        if not isinstance(interaction.channel, discord.Thread):
            logger.warning("Menu command used outside of a thread.")
            embed = simple_embed(CAN_ONLY_BE_USED_IN_THREAD, color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if interaction.channel.parent_id != int(TICKET_CHANNEL_ID):
            logger.warning("Menu command used in a thread not under the ticket channel.")
            embed = simple_embed(CAN_ONLY_BE_USED_IN_THREAD, color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        user = interaction.user
        if not user.guild_permissions.kick_members:
            embed = simple_embed(f"{NO_PERMISSION}", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        logger.info(f"Management menu selected by {interaction.user} in thread {interaction.channel}.")
        
        embed = discord.Embed(
            title="⚒️ Management Menu",
            description="sigma",
            color=0x5865F2
        )
        
        await interaction.response.send_message(embed=embed, view=TicketModMenu(ticketcog=self, bot=self.bot), ephemeral=True, delete_after=60)
        
        logger.info(f"Ticket menu selection sent to {interaction.user} in thread {interaction.channel}.")

    @commands.Cog.listener(name="THREAD_UPDATE")
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        guild = after.guild
        if not before.archived and after.archived:
            logger.info(f"Thread {after.name} archived. Checking members for removal.")
            for member in after.members:
                guild_member = guild.get_member(member.id)
                has_required_role = guild_member.guild_permissions.kick_members

                if not has_required_role:
                    embed = simple_embed(TICKET_CLOSED_TIMEOUT, color=0xffaa00)
                    await after.send(embed=embed, view=None)
                    await after.remove_user(guild_member)
                    logger.info(f"Removed user {guild_member} from archived thread {after.name}.")
                else:
                    logger.debug(f"User {guild_member} has required role, not removed from thread {after.name}.")

    async def cog_load(self):
        self.bot.tree.add_command(self.setup, guild=discord.Object(id=SYNC_SERVER))
        self.bot.tree.add_command(self.menu, guild=discord.Object(id=SYNC_SERVER))
        logger.info("TicketCog commands loaded to bot tree.")