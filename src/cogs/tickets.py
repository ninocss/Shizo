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
            color=0x00ff00
        )
        embed.set_author(
            name=f"{BOT_NAME}", 
            icon_url=interaction.client.user.avatar.url if interaction.client.user.avatar else None
        )
        
        embed.set_footer(
            text=f"{EMBED_FOOTER}",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )

        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
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

            embed_color = fields.get("color", 0x00D166)
            embed = discord.Embed(
                title=f"{TICKET_OVERVIEW_TITLE}",
                description=f"{CLOSE_EMBED_DESC}",
                color=embed_color
            )
            embed.set_footer(
                text=f"{EMBED_FOOTER}",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            embed.set_author(
                name=f"{interaction.user.name}", 
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            # set a category thumbnail if available in the ticket image map
            try:
                img_url = TICKET_IMAGE_MAP.get(title)
            except Exception:
                img_url = None

            if img_url:
                embed.set_image(url=img_url)

            for name, value in fields.items():
                if name in ["Title", "Rolle", "message", "color"]:
                    continue

                if not isinstance(value, str):
                    continue

                if not value.strip():
                    continue

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
            try:
                if title == "Kreativ-Server":
                    setup_desc = (
                        "Du hast ein Anliegen zu unserem Kreativ-Server?\n\n"
                        "Worum geht es?\n"
                        "- Wähle eine Option aus dem Drop-Down Menü aus!"
                    )
                    setup_embed = discord.Embed(title="MC Server: Kreativ-Server", description=setup_desc, color=embed_color)
                    await thread.send(embed=setup_embed, view=MCServerSetupView(ticketcog=self, server_type="kreativ"))
                elif title == "Survival (normal)":
                    setup_desc = (
                        "Du hast ein Anliegen zu unserem normal Freebuild Survival-Server?\n\n"
                        "Worum geht es?\n"
                        "- Wähle eine Option aus dem Drop-Down Menü aus!"
                    )
                    setup_embed = discord.Embed(title="MC Server: Survival (normal)", description=setup_desc, color=embed_color)
                    await thread.send(embed=setup_embed, view=MCServerSetupView(ticketcog=self, server_type="survival"))
                elif title == "Survival (Skyblock)":
                    setup_desc = (
                        "Du hast ein Anliegen zu unserem Skyblock-Bereich auf dem Survival-Server?\n\n"
                        "Worum geht es?\n"
                        "- Wähle eine Option aus dem Drop-Down Menü aus!"
                    )
                    setup_embed = discord.Embed(title="MC Server: Survival (Skyblock)", description=setup_desc, color=embed_color)
                    await thread.send(embed=setup_embed, view=MCServerSetupView(ticketcog=self, server_type="skyblock"))
                elif title == "Events":
                    setup_desc = (
                        "Auf unserem Minecraft-Server finden regelmäßig verschiedene Events statt. Große Minecraft-Gottesdienste gibt es zum Beispiel zu Ostern, Pfingsten, im Sommer oder zu Weihnachten. Diese werden dann auf unserer Webseite und hier im Discord in #neuigkeiten angekündigt.\n\n"
                        "Um welche Events geht es?\n- Wähle eine Option aus dem Drop-Down Menü aus!"
                    )
                    setup_embed = discord.Embed(title="MC Server: Events", description=setup_desc, color=embed_color)
                    await thread.send(embed=setup_embed, view=MCServerSetupView(ticketcog=self, server_type="events"))
                elif title == "Bug-Report":
                    bug_desc = (
                        "Du möchtest einen Bug auf unserem Minecraft-Server melden? Wenn der Fehler nicht kritisch ist oder dich nicht nur im Einzelnen betrifft, kannst du diesen Bug-Report auch gerne im #feedback Forum hier im Discord posten.\n\n"
                        "Beschreibe ansonsten nun hier den Vorfall. Was genau ist passiert und wann ist es passiert? Oft ist es auch relevant, auf welchem Unter-Server und in welcher Welt du das Problem hattest. Oder in welcher Minecraft-Edition (Java oder Bedrock) und in welcher Minecraft-Version du spielst. Wenn möglich, kannst du hier auch gerne Screenshots von dem Fehler schicken. Vielen Dank!"
                    )
                    bug_embed = discord.Embed(title="MC Server: Bug-Report", description=bug_desc, color=embed_color)
                    await thread.send(embed=bug_embed)
                elif title in ("Launcher & Mods", "Minecraft Launcher und Mods"):
                    lm_desc = (
                        "Du hast inhaltliche Fragen zu bekannten Minecraft-Launcher, Mod-Packs oder Mods? Oder Probleme bei der Installation oder Verwendung? Dann kannst du diese gerne hier stellen.\n\n"
                        "In unserem Minecraft Regelwerk ist beschrieben, wann welche Art von Client-Modifikationen (Mods) auf unserem Server erlaubt oder verboten sind. Im Zweifel kannst du hier gerne entsprechend nachfragen."
                    )
                    lm_embed = discord.Embed(title="Minecraft Launcher und Mods", description=lm_desc, color=embed_color)
                    await thread.send(embed=lm_embed)
                elif title == "Vor-Ort Treffen und Besuch":
                    meetup_desc = (
                        "Der Minecraft-Server Canstein-Berlin gehört zum Bibellabor der von Cansteinschen Bibelanstalt in Berlin e.V. Mehrmals im Jahr bieten wir als Verein Community-Treffen (Reallife-Treffen) in unserem Vereins-Sitz in Berlin an. Ebenso gibt es Auswärts-Termine, bei denen wir als Bibellabor an einem externen Veranstaltungs-Ort etwas anbieten und dort anzutreffen sind.\n\n"
                        "Um welche der geplanten Veranstaltungen geht es? - Wähle eine Option aus dem Drop-Down Menü aus!"
                    )
                    meetup_embed = discord.Embed(title="Vor-Ort Treffen und Besuch", description=meetup_desc, color=embed_color)
                    await thread.send(embed=meetup_embed, view=MCServerSetupView(ticketcog=self, server_type="events"))
            except Exception:
                logger.exception("Failed to send setup/embed submenu message in ticket thread")
            
            success_embed = simple_embed(TICKET_CREATION_SUCCESS.format(thread=thread.mention), color=0x00ff00)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=success_embed, ephemeral=True, delete_after=20)
                else:
                    await interaction.followup.send(embed=success_embed, ephemeral=True, delete_after=20)
            except Exception:
                # Last-resort: try followup if response failed
                try:
                    await interaction.followup.send(embed=success_embed, ephemeral=True, delete_after=20)
                except Exception:
                    logger.debug("Failed to send ticket creation confirmation")
            logger.info(f"Ticket thread '{thread.name}' created for user {interaction.user}.")

        except Exception as e:
            logger.error(f"Error creating ticket thread for user {interaction.user}: {e}")
            error_embed = simple_embed(TICKET_CREATION_ERROR, color=0xff0000)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=10)
                else:
                    await interaction.followup.send(embed=error_embed, ephemeral=True, delete_after=10)
            except Exception:
                try:
                    await interaction.followup.send(embed=error_embed, ephemeral=True, delete_after=10)
                except Exception:
                    logger.debug("Failed to send ticket creation error message")
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