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

        # only support/staff may use these quick message commands
        if not message.author.guild_permissions.kick_members:
            return

        content = message.content.strip()
        lc = content.lower()

        # === close command (existing behaviour) ===
        if lc.startswith("?close") or lc.startswith("?c"):
            if not isinstance(message.channel, discord.Thread):
                logger.warning("Close command used outside of a thread.")
                embed = simple_embed(CAN_ONLY_BE_USED_IN_THREAD, color=0xff0000)
                await message.channel.send(embed=embed)
                return

            if message.channel.parent_id != int(TICKET_CHANNEL_ID):
                logger.warning("Close command used in a thread not under the ticket channel.")
                embed = simple_embed(CAN_ONLY_BE_USED_IN_THREAD, color=0xff0000)
                await message.channel.send(embed=embed)
                return

            cancel_btn = Button(emoji=UNCHECK, label=CANCEL_BUTTON_LABEL, style=SECONDARY)
            cancel_btn.callback = self.cancel_btn_callback

            view = PersistentCloseView(ticketcog=self, bot=self.bot)
            view.add_item(cancel_btn)

            ticket_creator = get_ticket_creator(message.channel.id)

            await message.channel.send(view=view, content=f"{TICKET_CLOSE_PROMPT}".format(ticket_creator=ticket_creator))
            return

        # === rename via message: '?rename Neuer Name' or '?r Neuer Name' ===
        if lc.startswith("?rename ") or lc.startswith("?r "):
            if not isinstance(message.channel, discord.Thread):
                logger.warning("Rename command used outside of a thread.")
                embed = simple_embed(CAN_ONLY_BE_USED_IN_THREAD, color=0xff0000)
                await message.channel.send(embed=embed)
                return

            if message.channel.parent_id != int(TICKET_CHANNEL_ID):
                logger.warning("Rename command used in a thread not under the ticket channel.")
                embed = simple_embed(CAN_ONLY_BE_USED_IN_THREAD, color=0xff0000)
                await message.channel.send(embed=embed)
                return

            parts = content.split(" ", 1)
            if len(parts) < 2 or not parts[1].strip():
                embed = simple_embed("Bitte gib einen neuen Namen an, z.B. '?rename Neues Ticket'", color=0xffa500)
                await message.channel.send(embed=embed)
                return

            new_name = parts[1].strip()[:100]
            try:
                await message.channel.edit(name=new_name)
                embed = simple_embed(f"🎫 Ticket umbenannt zu: {new_name}", color=0x00ff00)
                await message.channel.send(embed=embed)
                logger.info(f"Ticket {message.channel.id} renamed to {new_name} by {message.author}")
            except Exception as e:
                logger.exception(f"Error renaming thread: {e}")
                embed = simple_embed(f"Fehler beim Umbenennen: {e}", color=0xff0000)
                await message.channel.send(embed=embed)
            return

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
                elif title == "Minecraft Launcher und Mods":
                    lm_desc = (
                        "Du hast inhaltliche Fragen zu bekannte Minecraft-Launcher, Mod-Packs oder Mods? Oder Probleme bei der Installation oder Verwendung? Dann kannst du diese gerne hier stellen.\n\n"
                        "In unserem Minecraft Regelwerk unter https://docu.canstein-berlin.de/rules/minecraft/#3-modifikationen ist beschrieben, wann welche Art von Client-Modifikationen (Mods) auf unserem Server erlaubt oder verboten sind. Im Zweifel kannst du hier gerne entsprechend nachfragen."
                    )
                    lm_embed = discord.Embed(title="Minecraft Launcher und Mods", description=lm_desc, color=embed_color)
                    lm_embed.set_footer(text=EMBED_FOOTER)
                    lm_embed.timestamp = discord.utils.utcnow()
                    await thread.send(embed=lm_embed)
                elif title == "Vor-Ort Treffen und Besuch":
                    meetup_desc = (
                        "Der Minecraft-Server _Canstein-Berlin_ gehört zum Bibellabor der **von Cansteinschen Bibelanstalt in Berlin e.V.**. Mehrmals im Jahr bieten wir als Verein Community-Treffen (Reallife-Treffen) in unserem Vereins-Sitz in Berlin an. Ebenso gibt es Auswärts-Termine, bei denen wir als Bibellabor an einem externen Veranstaltungs-Ort etwas anbieten und dort anzutreffen sind - ob als Besucher oder zum Mithelfen. Community-Treffen solcher Art werden allgemein im #neuigkeiten Channel hier im Discord verkündet. Fragen zu diesen Treffen können via E-Mail an communitytreffen@canstein-berlin.de oder über das Ticket hier direkt gestellt werden.\n\n"
                        "Wir sind aber auch auf Anfrage in Berlin besuchbar und bieten an, sich bei uns das 'analoge Bibellabor' samt unserer Schreibwerkstatt in der Philipp-Melanchthon-Kirche in Berlin-Neukölln anzusehen. Hierfür kann man sich an unsere Mitarbeiter via E-Mail an kontakt@canstein-berlin.de oder über das Support-Ticket hier wenden.\n\n"
                        "Um welche der geplanten Veranstaltungen geht es?\n- Wähle eine Option aus dem Drop-Down Menü aus!"
                    )
                    meetup_embed = discord.Embed(title="Vor-Ort Treffen und Besuch", description=meetup_desc, color=embed_color)
                    meetup_embed.set_footer(text=EMBED_FOOTER)
                    meetup_embed.timestamp = discord.utils.utcnow()
                    await thread.send(embed=meetup_embed, view=MCServerSetupView(ticketcog=self, server_type="meetup"))
                elif title == "Regelverstoß / Spieler melden":
                    report_desc = (
                        "**Eindeutigen Regelverstoß melden**\n"
                        "Möchtest du einen Regelverstoß eines Spielers melden? Dann hast du hier die Möglichkeit dazu! Beschreibe bitte genau den Vorfall: Was ist genau passiert? Wann ist es in etwa passiert und wo ist es passiert? Wer war daran beteiligt? Kannst du uns vielleicht sogar Screenshots, eine Replay-Aufnahme oder andere Beweise liefern? Gibt es Zeugen oder eine Vorgeschichte? Unser Support-Team steht dir hier gerne zur Verfügung. Wir nehmen Regelverstöße sehr ernst. Danke für dein Vertrauen!\n\n"
                        "**Spieler melden**\n"
                        "Gibt es Streifälle oder möchtest du eine Beschwerde gegen jemand anderen einreichen? Dann hast du hier die Möglichkeit dazu! Schreibe bitte um wen es geht und was genau passiert ist. Sind noch andere Personen dabei beteiligt? Gibt es eine Vorgeschichte? Was würdest du von dieser Person erwarten?"
                    )
                    report_embed = discord.Embed(title="Regelverstoß / Spieler melden", description=report_desc, color=embed_color)
                    report_embed.set_footer(text=EMBED_FOOTER)
                    report_embed.timestamp = discord.utils.utcnow()
                    await thread.send(embed=report_embed)
                elif title == "Entbannungsantrag":
                    unban_desc = (
                        "Du wurdest **auf unserem Minecraft-Server** gebannt und möchtest einen Entbannungsantrag schreiben oder Einspruch gegen deinen Bann erheben? Wir bannen nicht ohne Grund. Lese dir unsere Regeln (https://docu.canstein-berlin.de/rules) durch und schreibe uns hier deinen Antrag. Wir werden intern darüber abstimmen und uns bei dir melden.\n\n"
                        "Erwähne in deinem Antrag bitte auch, wie du in Minecraft heißt und wann du in etwa gebannt wurdest."
                    )
                    unban_embed = discord.Embed(title="Entbannungsantrag", description=unban_desc, color=embed_color)
                    unban_embed.set_footer(text=EMBED_FOOTER)
                    unban_embed.timestamp = discord.utils.utcnow()
                    await thread.send(embed=unban_embed)
                elif title == "Kooperationen":
                    coop_desc = (
                        "Der Minecraft-Server _Canstein-Berlin_ gehört zum Bibellabor der **von Cansteinschen Bibelanstalt in Berlin e.V.**. Wir als Verein bieten externen Organisationen (Kirchengemeinde, Arbeitsgemeinschaft, Schulklasse, Konfi-Gruppe, Verein, …) Kooperation verschiedener Art an, um biblische / pädagogische / didaktische Minecraft-Projekte gemeinsam durchzuführen. Wir bieten beispielsweise Workshops und Platz für Bau-Events an, oder stellen bei langfristigen Kooperationen auch Platz und Rechte auf unserem Minecraft Kooperations-Server zur Verfügung.\n\n"
                        "Alle Infos rund um unsere Kooperations-Angebote finden Sie in unserer Doku: https://docu.canstein-berlin.de/supplies.\n\n"
                        "Bei Fragen können Sie sich gerne per E-Mail an kontakt@canstein-berlin.de oder hier im Support-Ticket an uns wenden."
                    )
                    coop_embed = discord.Embed(title="Kooperationen", description=coop_desc, color=embed_color)
                    coop_embed.set_footer(text=EMBED_FOOTER)
                    coop_embed.timestamp = discord.utils.utcnow()
                    await thread.send(embed=coop_embed)
                elif title == "Bewerbung":
                    apply_desc = (
                        "Du möchtest dich bei uns auf dem Minecraft-Server **als Bauhilfe** oder **im Team** mit einbringen? Oder möchtest du eine feste Aufgabe bei Vor-Ort Projekte in Berlin übernehmen? Wir freuen uns über dein Engagement!\n\n"
                        "Du kannst hier **allgemeine Fragen** zum entsprechenden Rang oder zum **Bewerbungs-Verfahren** stellen. Für die Bewerbung selber ist aber unser Online-Formular zu verwenden: https://canstein-berlin.de/minecraft-bewerbung. Wenn deine gewünschte Rolle dort namentlich nicht aufgeführt wird, kannst du dich gerne hier bei uns melden.\n\n"
                        "Um welchen Rang geht es?\n- Wähle eine Option aus dem Drop-Down Menü aus!"
                    )
                    apply_embed = discord.Embed(title="Bewerbung", description=apply_desc, color=embed_color)
                    apply_embed.set_footer(text=EMBED_FOOTER)
                    apply_embed.timestamp = discord.utils.utcnow()
                    await thread.send(embed=apply_embed, view=MCServerSetupView(ticketcog=self, server_type="bewerbung"))
                elif title == "Account gehackt / neuer Account":
                    acc_desc = (
                        "Wurde dein Minecraft oder Discord-Account gehackt oder hast du keinen Zugriff mehr auf deinen Account? Wir können deinen alten Account zur Sicherheit sperren, damit keiner mit deinem Namen Unfug anstellt. Lass dir bei Zugriffs-Problemen gerne von unserem Support-Team helfen oder melde dich direkt bei Discord / Microsoft. Bei einem Account-Wechsel können wir deine Account-Daten (Rang, Grundstücke, Schematics etc.) auf den neuen Account transferieren lassen, wenn wir uns sicher sind, dass die Anfrage von der selben Person kommt.\n\n"
                        "Beschreibe uns deine Situation und nenne uns die zugehörigen Account-Namen."
                    )
                    acc_embed = discord.Embed(title="Account gehackt / neuer Account", description=acc_desc, color=embed_color)
                    acc_embed.set_footer(text=EMBED_FOOTER)
                    acc_embed.timestamp = discord.utils.utcnow()
                    await thread.send(embed=acc_embed)
                elif title == LABEL_DISCORD:
                    d_desc = "Bitte schildere dein Problem oder deine Frage. Wie können wir dir helfen? Was ist dein Anliegen?"
                    d_embed = discord.Embed(title=LABEL_DISCORD, description=d_desc, color=embed_color)
                    d_embed.set_footer(text=EMBED_FOOTER)
                    d_embed.timestamp = discord.utils.utcnow()
                    await thread.send(embed=d_embed)
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

    @app_commands.command(name="rename", description="Rename the current ticket thread")
    @app_commands.describe(new_name="Neuer Name des Tickets")
    async def rename(self, interaction: discord.Interaction, new_name: str):
        logger.info(f"Rename command invoked by {interaction.user} in channel {interaction.channel}.")

        if not isinstance(interaction.channel, discord.Thread):
            logger.warning("Rename command used outside of a thread.")
            embed = simple_embed(CAN_ONLY_BE_USED_IN_THREAD, color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if interaction.channel.parent_id != int(TICKET_CHANNEL_ID):
            logger.warning("Rename command used in a thread not under the ticket channel.")
            embed = simple_embed(CAN_ONLY_BE_USED_IN_THREAD, color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user = interaction.user
        if not user.guild_permissions.kick_members:
            embed = simple_embed(NO_PERMISSION, color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            await interaction.response.defer()
            await interaction.channel.edit(name=new_name[:100])
            await interaction.followup.send(simple_embed(f"🎫 Ticket umbenannt zu: {new_name}", color=0x00ff00), ephemeral=True)
            logger.info(f"Ticket {interaction.channel.id} renamed to {new_name} by {interaction.user}")
        except Exception as e:
            logger.exception(f"Error renaming thread via slash command: {e}")
            await interaction.followup.send(simple_embed(f"Fehler beim Umbenennen: {e}", color=0xff0000), ephemeral=True)

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
        # add rename slash command for supporters
        try:
            self.bot.tree.add_command(self.rename, guild=discord.Object(id=SYNC_SERVER))
        except Exception:
            logger.debug("Failed to add rename command to tree (may already exist)")
        logger.info("TicketCog commands loaded to bot tree.")