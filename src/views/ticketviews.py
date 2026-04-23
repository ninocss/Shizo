# ruff: noqa: F403 F405
import discord
from discord.ui import View, Button
from util.constants import *
from modals.ticketmodals import *
from typing import TYPE_CHECKING
from util.tickets.ticket_creator import get_ticket_creator, delete_ticket_creator
from lang.texts import *
import asyncio
import logging
import colorlog

if TYPE_CHECKING:
    from cogs.tickets import TicketCog
    from cogs.music import MusicCog
import re

async def closeTicket(self, interaction: discord.Interaction, reason: str = None):
    guild = interaction.guild
    TICKET_CREATOR_ID = get_ticket_creator(interaction.channel.id) 
    if TICKET_CREATOR_ID is None:
        logger.warning(f"Ticket creator ID not found for channel {interaction.channel.id}")
        embed = discord.Embed(
            title=f"{ERROR}",
            description="Das Mitglied wurde nicht gefunden.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    TICKET_CREATOR = guild.get_member(TICKET_CREATOR_ID)
    # fallback to fetching the member in case they`re not in the bot`s member cache
    if TICKET_CREATOR is None:
        try:
            TICKET_CREATOR = await guild.fetch_member(TICKET_CREATOR_ID)
        except Exception:
            logger.warning(f"Ticket creator not found in guild for ID {TICKET_CREATOR_ID}")
            embed = discord.Embed(
                title=f"{ERROR}",
                description="Das Mitglied wurde nicht gefunden.",
                color=0xff0000
            )
    logger.info(f"closeTicket: channel={interaction.channel} channel_id={getattr(interaction.channel, 'id', None)} ticket_creator_id={TICKET_CREATOR_ID} invoked_by={interaction.user}")
    # prepare reason text for embeds/DMs
    reason_text = reason if reason and str(reason).strip() else "Keine Angabe"
    # Explicitly remove the original ticket creator unless they are in the support/admin team
    try:
        if TICKET_CREATOR is not None:
            creator_is_support = (
                TICKET_CREATOR.guild_permissions.administrator or
                any(role.name in [TEAM_ROLE, MOD, TRAIL_MOD] for role in TICKET_CREATOR.roles)
            )

            logger.info(f"Resolved ticket creator: {TICKET_CREATOR} (id={getattr(TICKET_CREATOR, 'id', None)}) support={creator_is_support}")
            # log current channel members (ids and display names) to diagnose membership checks
            try:
                members_info = []
                for m in interaction.channel.members:
                    m_id = getattr(m, 'id', None) or (getattr(getattr(m, 'user', None), 'id', None))
                    m_name = getattr(m, 'display_name', None) or getattr(getattr(m, 'user', None), 'name', None)
                    members_info.append(f"{m_name}({m_id})")
                logger.info(f"Channel members: {', '.join(members_info)}")
            except Exception:
                logger.debug("Could not enumerate channel members for logging")

            if not creator_is_support:
                try:
                    if isinstance(interaction.channel, discord.Thread) and any((getattr(m, 'id', None) == getattr(TICKET_CREATOR, 'id', None)) or (getattr(getattr(m, 'user', None), 'id', None) == getattr(TICKET_CREATOR, 'id', None)) for m in interaction.channel.members):
                        logger.info(f"Removing ticket creator {TICKET_CREATOR} (id={TICKET_CREATOR.id}) from ticket channel {interaction.channel}")
                        await interaction.channel.remove_user(TICKET_CREATOR)
                        await asyncio.sleep(0.5)

                        if SEND_TICKET_FEEDBACK:
                            dm_embed = discord.Embed(
                                title=f"{LOCK_EMOJI} Ticket geschlossen - {interaction.channel.name}",
                                description=f"**Geschlossen von:** {interaction.user.mention}\n**Grund:** {reason_text}\n**Server:** {interaction.guild.name}",
                                color=0xff0000
                            )
                            dm_embed.set_thumbnail(url=interaction.guild.icon)
                            dm_embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
                            dm_embed.set_footer(text=EMBED_FOOTER)
                            dm_embed.timestamp = discord.utils.utcnow()
                            logger.info(f"Sending closed ticket embed to creator {TICKET_CREATOR}")
                            try:
                                await TICKET_CREATOR.send(embed=dm_embed)
                            except Exception:
                                logger.debug(f"Could not DM ticket creator {TICKET_CREATOR}")
                except Exception as e:
                    logger.error(f"Error removing ticket creator: {e}")

    except Exception:
        # don`t fail closing completely if something goes wrong while handling the creator
        logger.exception("Unexpected error while handling ticket creator removal")

    # Remove any non-support members from the thread (skip the creator if already removed)
    for member in list(interaction.channel.members):
        # member may be a User; resolve to guild member
        guild_member = guild.get_member(member.id)
        if guild_member is None:
            continue

        # skip original creator if it`s the same member (we already handled them)
        if TICKET_CREATOR is not None and guild_member.id == TICKET_CREATOR.id:
            continue

        has_required_role = any(role.name in [TEAM_ROLE, MOD, TRAIL_MOD] for role in guild_member.roles)

        if not has_required_role:
            logger.info(f"Removing user {guild_member} from ticket channel {interaction.channel} (has_required_role={has_required_role})")
            try:
                await interaction.channel.remove_user(guild_member)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.exception(f"Could not remove user {guild_member}: {e}")

            if SEND_TICKET_FEEDBACK is True:
                embed = discord.Embed(
                    title=f"{LOCK_EMOJI} Ticket geschlossen - {interaction.channel.name}",
                    description=f"**Geschlossen von:** {interaction.user.mention}\n**Grund:** {reason_text}\n**Server:** {interaction.guild.name}",
                    color=0xff0000
                )
                embed.set_thumbnail(url=interaction.guild.icon)
                embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
                embed.set_footer(text=EMBED_FOOTER)
                embed.timestamp = discord.utils.utcnow()
                logger.info(f"Sending closed ticket embed to {guild_member}")
                try:
                    await guild_member.send(embed=embed)
                except Exception:
                    logger.debug(f"Could not DM user {guild_member}")
        else:
            logger.debug(f"User {guild_member} has required role, not removing from ticket channel")
        
    if not interaction.channel.name.startswith("[CLOSED] "):
        if reason and str(reason).strip():
            # Escape triple-backticks in the reason to avoid breaking the surrounding codeblock
            safe_reason = reason.replace("```", "`\u200b``")
            reason_value = f"```{safe_reason}```"
            close_embed = discord.Embed(
                title=f"{LOCK_EMOJI} Ticket geschlossen",
                description=f"Ticket geschlossen von {interaction.user.mention} aus folgendem Grund:\n{reason_value}",
                color=0xff0000
            )
        else:
            close_embed = discord.Embed(
                title=f"{LOCK_EMOJI} Ticket geschlossen",
                description=f"Ticket geschlossen von {interaction.user.mention}.",
                color=0xff0000
            )
        close_embed.add_field(
            name="📊 Ticket Information",
            value=f"**Channel:** {interaction.channel.name}\n**Closed at:** <t:{int(discord.utils.utcnow().timestamp())}:F>",
            inline=False
        )
        close_embed.add_field(
            name="👤 Closed by",
            value=f"{interaction.user.mention}",
            inline=True
        )
        if TICKET_CREATOR:
            close_embed.add_field(
                name="🎫 Original Creator",
                value=f"{TICKET_CREATOR.mention}",
                inline=True
            )
        
        message_count = 0
        member_count = len(interaction.channel.members)
        try:
            async for _ in interaction.channel.history(limit=None):
                message_count += 1
        except:
            message_count = "Unknown"
        
        close_embed.add_field(
            name="📈 Channel Statistics",
            value=f"**Messages:** {message_count}\n**Members:** {member_count}\n**Created:** <t:{int(interaction.channel.created_at.timestamp())}:R>",
            inline=True
        )
        
        support_members = []
        for member in interaction.channel.members:
            guild_member = interaction.guild.get_member(member.id)
            if guild_member and any(role.name in [TEAM_ROLE, MOD, TRAIL_MOD] for role in guild_member.roles):
                support_members.append(guild_member)
                
        if support_members:
            support_list = ", ".join([member.mention for member in support_members[:3]])
            if len(support_members) > 3:
                support_list += f" +{len(support_members) - 3} more"
            close_embed.add_field(
                name="🛠️ Support Team",
                value=support_list,
                inline=False
            )
        try:
            logger.info(f"Renaming channel {interaction.channel} to closed")
            await interaction.channel.edit(name=f"[CLOSED] {interaction.channel.name}")
            await asyncio.sleep(0.5)

            await interaction.channel.send(embed=close_embed, view=CloseThreadView(ticketcog=self.ticketcog, bot=self.bot))
        except discord.HTTPException as e:
            logger.error(f"HTTPException while closing ticket: {e}")
            if e.status == 429:
                await asyncio.sleep(e.retry_after if hasattr(e, 'retry_after') else 1)
                await interaction.channel.edit(name=f"[CLOSED] {interaction.channel.name}")
                await asyncio.sleep(0.5)
                await interaction.channel.send(embed=close_embed, view=CloseThreadView(ticketcog=self.ticketcog, bot=self.bot))
            else:
                await interaction.channel.send(embed=close_embed, view=CloseThreadView(ticketcog=self.ticketcog, bot=self.bot))
    
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
class ActionsView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.song_history = []

        ins_song_btn = Button(label="Inspire Me", emoji="✨", style=GREEN, custom_id="ran_song_btn", row=0)
        ins_song_btn.callback = self.ran_song

        mostplayed_btn = Button(label="Most Played", emoji="🏆", style=PURPLE, custom_id="mostplayed_btn", row=0)
        mostplayed_btn.callback = self.mostplayed

        charts_btn = Button(label="Charts", emoji="🎶", style=SECONDARY, custom_id="charts_btn", row=1)
        charts_btn.callback = self.charts_song

        history_btn = Button(label="History", emoji="📖", style=SECONDARY, custom_id="history_btn", row=1)
        history_btn.callback = self.history_call

        self.add_item(ins_song_btn)
        self.add_item(mostplayed_btn)
        self.add_item(charts_btn)
        self.add_item(history_btn)

    async def mostplayed(self, interaction: discord.Interaction):
        history = await self.get_history(interaction)

        if not history:
            embed = discord.Embed(
                title="❌ No History Found",
                description="I couldn`t find any songs in the recent history.",
                color=0xff0000
            )
            embed.set_footer(text="Try playing some music first!")
            embed.timestamp = discord.utils.utcnow()
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        song_counts = {}
        for song in history:
            song_counts[song] = song_counts.get(song, 0) + 1

        sorted_songs = sorted(song_counts.items(), key=lambda x: x[1], reverse=True)

        lines = []
        for i, (song, count) in enumerate(sorted_songs[:10], 1):
            rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🎵"
            lines.append(f"{rank_emoji} **{i}.** {song} • `{count}×`")

        embed = discord.Embed(
            title="🏆 Most Played Songs",
            description="\n".join(lines),
            color=0xff6b6b
        )
        embed.add_field(
            name="📊 Statistics",
            value=f"• Unique songs: **{len(song_counts)}**\n• Total plays: **{sum(song_counts.values())}**",
            inline=True
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="Tap a button below to play a top track.")
        embed.timestamp = discord.utils.utcnow()

        view = self.MostPlayedView(self.bot, sorted_songs[:3])
        await interaction.followup.send(embed=embed, view=view)

    class MostPlayedView(View):
        def __init__(self, bot, top_songs):
            super().__init__(timeout=300)
            self.bot = bot

            for i, (song, _) in enumerate(top_songs):
                display_name = song[:40] + "…" if len(song) > 40 else song
                rank_emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
                button = Button(
                    label=f"{display_name}",
                    style=GREEN,
                    emoji=rank_emoji,
                    row=0
                )
                button.callback = self.create_play_callback(song)
                self.add_item(button)

            refresh_btn = Button(label="Refresh", emoji="🔄", style=SECONDARY, row=1)
            refresh_btn.callback = self.refresh_callback
            self.add_item(refresh_btn)

        def create_play_callback(self, song: str):
            async def play_callback(interaction: discord.Interaction):
                music_cog = self.bot.get_cog("MusicCog")
                if music_cog:
                    await music_cog.mostplayed_callback(interaction, song)
                else:
                    embed = discord.Embed(
                        title="Error",
                        description="Music system is currently unavailable.",
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            return play_callback

        async def refresh_callback(self, interaction: discord.Interaction):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Refreshed",
                    description="Please re-open Most Played to fetch latest stats.",
                    color=0x4ecdc4
                ),
                ephemeral=True,
                delete_after=6
            )

    async def get_history(self, interaction: discord.Interaction) -> list:
        if not interaction.response.is_done():
            await interaction.response.defer()
        history_list = []

        channel = None
        try:
            channel = await self.bot.fetch_channel(I_CHANNEL)
        except Exception as e:
            logger.error(f"get_history fetch_channel error: {e}")

        if channel:
            try:
                async for message in channel.history(limit=300):
                    if (
                    message.author == self.bot.user and
                    message.embeds
                    ):
                        embed = message.embeds[0]
                        if embed.title and embed.title.lower().strip() == "now playing":
                            desc = embed.description or ""
                            song_name = None

                            m = re.search(r"\*\*(.*?)\*\*", desc)
                            if m:
                                song_name = m.group(1).strip()
                            else:
                                idx = desc.lower().find("now playing:")
                                if idx != -1:
                                    after = desc[idx + len("now playing:"):].strip()
                                    song_name = after.splitlines()[0].strip().strip("* ").strip()
                                else:
                                    song_name = desc.splitlines()[0].strip()

                            if song_name:
                                history_list.append(song_name)
            except Exception as e:
                logger.error(f"get_history history parse error: {e}")

        self.song_history = history_list[::-1]
        return self.song_history

    async def ran_song(self, interaction: discord.Interaction):
        music_cog: "MusicCog" = self.bot.get_cog("MusicCog")
        if music_cog:
            await music_cog.insipre_me(interaction)
        else:
            embed = discord.Embed(
                title="Error",
                description="Music system is currently unavailable.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    async def charts_song(self, interaction: discord.Interaction):
        music_cog: "MusicCog" = self.bot.get_cog("MusicCog")
        if music_cog:
            await music_cog.play_chart.callback(music_cog, interaction)
        else:
            embed = discord.Embed(
                title="Error",
                description="Music system is currently unavailable.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    async def history_call(self, interaction: discord.Interaction):
        current_history = await self.get_history(interaction=interaction)

        if not current_history:
            embed = discord.Embed(
                title="No History Found",
                description="I couldn`t find any songs in the recent history.",
                color=0xff0000
            )
            embed.set_footer(text="Try playing some music first!")
            embed.timestamp = discord.utils.utcnow()
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        page_size = 10
        total_pages = (len(current_history) + page_size - 1) // page_size

        def create_history_embed(page: int = 0):
            start_idx = page * page_size
            end_idx = start_idx + page_size
            page_history = current_history[start_idx:end_idx]

            history_msg = "\n".join(
                [f"**{start_idx + i + 1}.** {song}" for i, song in enumerate(page_history)]
            )

            embed = discord.Embed(
                title="Song History",
                description=history_msg or "No entries on this page.",
                color=0x4ecdc4
            )
            embed.add_field(
                name="Info",
                value=f"Page **{page + 1}** of **{total_pages}** • Total: **{len(current_history)}**",
                inline=True
            )
            if interaction.guild and interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.set_footer(text="Use the buttons to navigate pages.")
            embed.timestamp = discord.utils.utcnow()
            return embed

        view = self.HistoryView(self.bot, current_history, create_history_embed, total_pages)
        embed = create_history_embed(0)
        await interaction.followup.send(embed=embed, view=view)

    class HistoryView(View):
        def __init__(self, bot, history, embed_func, total_pages: int):
            super().__init__(timeout=300)
            self.bot = bot
            self.history = history
            self.embed_func = embed_func
            self.total_pages = total_pages
            self.current_page = 0

            self.prev_btn = Button(emoji="⬅️", style=SECONDARY, disabled=True, label="Previous", row=0)
            self.prev_btn.callback = self.prev_page
            self.add_item(self.prev_btn)

            self.next_btn = Button(
                emoji="➡️",
                style=SECONDARY,
                disabled=(total_pages <= 1),
                label="Next",
                row=0
            )
            self.next_btn.callback = self.next_page
            self.add_item(self.next_btn)

        async def prev_page(self, interaction: discord.Interaction):
            if self.current_page > 0:
                self.current_page -= 1
                embed = self.embed_func(self.current_page)
                self.prev_btn.disabled = (self.current_page == 0)
                self.next_btn.disabled = (self.current_page >= self.total_pages - 1)
                await interaction.response.edit_message(embed=embed, view=self)

        async def next_page(self, interaction: discord.Interaction):
            if self.current_page < self.total_pages - 1:
                self.current_page += 1
                embed = self.embed_func(self.current_page)
                self.prev_btn.disabled = (self.current_page == 0)
                self.next_btn.disabled = (self.current_page >= self.total_pages - 1)
                await interaction.response.edit_message(embed=embed, view=self)
                
# Define all persistent views
class PersistentCloseView(View):
    def __init__(self, bot, ticketcog: "TicketCog"):
        super().__init__(timeout=None)
        self.ticketcog = ticketcog
        self.bot = bot
        
        close_btn = Button(label="Ticket schließen", style=DANGER, emoji=LOCK_EMOJI, custom_id="close_ticket_button")
        close_btn.callback = self.close_button
        
        close_reason_btn = Button(label="Ticket mit Grund schließen", style=SECONDARY, emoji=LOCK_W_REASON_EMOJI, custom_id="close_ticket_button_reason")
        close_reason_btn.callback = self.close_button_with_reason
        
        self.add_item(close_btn)
        self.add_item(close_reason_btn)
    
    async def close_button(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} clicked close_button in {interaction.channel}")
        embed = discord.Embed(
            title="🔒 Ticket schließen",
            description=f"{interaction.user.mention} Bist du dir sicher, dass du das Ticket schließen möchtest?",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, view=CloseConfirmView(ticketcog=self.ticketcog, bot=self.bot))
    
    async def close_button_with_reason(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} clicked close_button_with_reason in {interaction.channel}")
        await interaction.response.send_modal(closeThreadReasonModal(ticketcog=self.ticketcog))

# The close view, with a reason
class CloseReasonConfirmView(View):
    def __init__(self, bot, ticketcog: "TicketCog", reason: str = ""):
        super().__init__(timeout=180)
        self.bot = bot
        self.reason = reason
        self.ticketcog = ticketcog
        
        yes_button = Button(emoji=CHECK, style=DANGER, label="Ja, schließen")
        yes_button.callback = self.yes_button
        
        no_button = Button(emoji=UNCHECK, style=SECONDARY, label="Nein")
        no_button.callback = self.no_button
        
        self.add_item(yes_button)
        self.add_item(no_button)
        
    async def yes_button(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} confirmed closing ticket with reason `{self.reason}` in {interaction.channel}")
        await interaction.message.delete()
        global DELETE_USER
        DELETE_USER = interaction.user
        # Delegate to shared close handler, passing the reason
        await closeTicket(self, interaction=interaction, reason=self.reason)

    async def no_button(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} cancelled closing ticket with reason in {interaction.channel}")
        await interaction.message.delete()

# The close view, if you closed a ticket
class CloseThreadView(View):
    def __init__(self, bot, ticketcog: "TicketCog"):
        super().__init__(timeout=None)
        self.ticketcog = ticketcog
        self.bot = bot
        
        archive_button = Button(emoji=ARCHIVE_EMOJI, style=SECONDARY, label="Archivieren", custom_id="archive_ticket_button")
        archive_button.callback = self.archive_button
        
        delete_button = Button(emoji=TRASHCAN_EMOJI, style=DANGER, label="Löschen", custom_id="delete_ticket_button")
        delete_button.callback = self.delete_button
        
        trans_button = Button(emoji=TRANSCRIPT_EMOJI, style=SECONDARY, label="Transkribieren", custom_id="transcript_ticket_button")
        trans_button.callback = self.trans_button
        
        reopen_button = Button(emoji=REOPEN_EMOJI, style=GREEN, label="Neu eröffnen", custom_id="reopen_ticket_button")
        reopen_button.callback = self.reopen_button

        self.add_item(delete_button)
        self.add_item(reopen_button)
        self.add_item(trans_button)
        self.add_item(archive_button)
        
    async def archive_button(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} clicked archive_button in {interaction.channel}")
        if not (
            interaction.user.guild_permissions.administrator or
            any(role.name in [MOD, TRAIL_MOD] for role in interaction.user.roles)
        ):
            logger.warning(f"{interaction.user} tried to archive ticket without permission in {interaction.channel}")
            embed = discord.Embed(
                title="❌ Keine Berechtigung",
                description=NO_PERMISSION,
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
            return
        
        await interaction.response.send_modal(ThreadModalRename())

    async def delete_button(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} clicked delete_button in {interaction.channel}")
        if not (
            interaction.user.guild_permissions.administrator or
            any(role.name in [MOD, TRAIL_MOD] for role in interaction.user.roles)
        ):
            logger.warning(f"{interaction.user} tried to delete ticket without permission in {interaction.channel}")
            embed = discord.Embed(
                title="❌ Keine Berechtigung",
                description=NO_PERMISSION,
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
            return

        embed = discord.Embed(
            title="🗑️ Ticket löschen",
            description=f"{interaction.user.mention} Möchtest du dieses Ticket wirklich löschen?",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, view=DeleteConfirmView(ticketcog=self.ticketcog))
        
    async def trans_button(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} clicked trans_button in {interaction.channel}")
        if not (
            interaction.user.guild_permissions.administrator or
            any(role.name in [MOD, TRAIL_MOD] for role in interaction.user.roles)
        ):
            logger.warning(f"{interaction.user} tried to transcribe ticket without permission in {interaction.channel}")
            embed = discord.Embed(
                title="❌ Keine Berechtigung",
                description=NO_PERMISSION,
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
            return
        
        await interaction.response.send_modal(TransDesc(bot=self.bot))

    async def reopen_button(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} clicked reopen_button in {interaction.channel}")
        if not (
            interaction.user.guild_permissions.administrator or
            any(role.name in [MOD, TRAIL_MOD] for role in interaction.user.roles)
        ):
            logger.warning(f"{interaction.user} tried to reopen ticket without permission in {interaction.channel}")
            embed = discord.Embed(
                title=NO_PERMISSION_TITLE,
                description=NO_PERMISSION,
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
            return
        
        guild = interaction.guild
        TICKET_CREATOR_ID = get_ticket_creator(interaction.channel.id) 
        if TICKET_CREATOR_ID is None:
            logger.warning(f"Ticket creator ID not found for channel {interaction.channel.id} on reopen")
            embed = discord.Embed(
                title="❌ Member nicht gefunden",
                description=NO_MEMBER,
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        TICKET_CREATOR = guild.get_member(TICKET_CREATOR_ID)
        if TICKET_CREATOR is None:
            try:
                TICKET_CREATOR = await guild.fetch_member(TICKET_CREATOR_ID)
            except Exception:
                logger.warning(f"Ticket creator not found in guild for ID {TICKET_CREATOR_ID}")

        if not any(role.name in [MOD, TRAIL_MOD] for role in interaction.user.roles):
            logger.warning(f"{interaction.user} tried to reopen ticket without support role in {interaction.channel}")
            embed = discord.Embed(
                title="❌ Keine Berechtigung",
                description=NO_PERMISSION,
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
            return
        
        if isinstance(interaction.channel, discord.Thread):
            bot_messages = []
            async for message in interaction.channel.history(limit=None):
                if message.author == interaction.client.user and message.embeds:
                    bot_messages.append(message)
                
                for message in bot_messages[1:]:
                    try:
                        await message.delete()
                        logger.debug(f"Deleted bot embed message in {interaction.channel}")
                    except Exception as e:
                        logger.error(f"Error deleting bot embed message: {e}")
                        
                current_channel_name = interaction.channel.name
                if current_channel_name.startswith("[CLOSED] "):
                    current_channel_name = current_channel_name[9:]
                    
                await interaction.channel.edit(name=current_channel_name)
                embed = discord.Embed(
                    title="✅ Setup abgeschlossen",
                    description="Alle Setup-Nachrichten im Ticket wurden gelöscht.",
                    color=0x00ff00
                )
                await interaction.followup.send_message(embed=embed, ephemeral=True, delete_after=20)
                
                await asyncio.sleep(0.5)
                await interaction.channel.add_user(TICKET_CREATOR)
                
                reopen_embed = discord.Embed(
                    title="🔓 Ticket wieder geöffnet",
                    description=f"{TICKET_CREATOR.mention} Das Ticket wurde wieder geöffnet.",
                    color=0x00ff00
                )
                await interaction.channel.send(embed=reopen_embed)
        
# The view, where you can deside between "yes" and "no"
class CloseConfirmView(View):
    def __init__(self, bot, ticketcog: "TicketCog", timeout = 180):
        super().__init__(timeout=timeout)
        self.ticketcog = ticketcog
        self.bot = bot
        
        yes_button = Button(emoji=CHECK, style=DANGER, label="Ja, schließen")
        yes_button.callback = self.yes_button
        
        no_button = Button(emoji=UNCHECK, style=SECONDARY, label="Nein")
        no_button.callback = self.no_button
        
        self.add_item(yes_button)
        self.add_item(no_button)
        
    async def yes_button(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} confirmed closing ticket without reason in {interaction.channel}")
        await interaction.message.delete()
        await closeTicket(self, interaction=interaction)
    
    async def no_button(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} cancelled closing ticket without reason in {interaction.channel}")
        await interaction.message.delete()

# Confirmation view for deleting a ticket
class DeleteConfirmView(View):
    def __init__(self, ticketcog: "TicketCog", timeout=180):
        super().__init__(timeout=timeout)
        self.ticketcog = ticketcog
        self.bot = ticketcog.bot if ticketcog and hasattr(ticketcog, 'bot') else None

        yes_button = Button(emoji=CHECK, style=DANGER, label="Ja, löschen")
        yes_button.callback = self.yes_button

        no_button = Button(emoji=UNCHECK, style=SECONDARY, label="Nein")
        no_button.callback = self.no_button

        self.add_item(yes_button)
        self.add_item(no_button)

    async def yes_button(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} confirmed deleting ticket in {interaction.channel}")
        # acknowledge the interaction before deleting the channel
        try:
            await interaction.response.send_message(embed=discord.Embed(title="✅ Ticket gelöscht", description="Das Ticket wird jetzt gelöscht."), ephemeral=True)
        except Exception:
            # fallback: try to delete the confirmation message
            try:
                await interaction.message.delete()
            except Exception:
                pass

        # remove mapping if present
        try:
            delete_ticket_creator(interaction.channel.id)
        except Exception:
            logger.debug("Could not delete ticket creator mapping")

        # finally delete the channel/thread
        try:
            await interaction.channel.delete()
            logger.info(f"Deleted ticket channel {interaction.channel}")
        except Exception as e:
            logger.exception(f"Failed to delete ticket channel: {e}")

    async def no_button(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} cancelled deleting ticket in {interaction.channel}")
        try:
            await interaction.message.delete()
        except Exception:
            pass

# The ticket-setup view
class TicketSetupView(View):
    def __init__(self, ticketcog: "TicketCog"):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown(ticketcog))

# The ticket-setup view dropdown
class TicketDropdown(discord.ui.Select):
    options = [
        discord.SelectOption(label="MC Server: Kreativ-Server", emoji="🚀", value="mc_kreativ", description="Grundstücke, Bau-Wettbewerbe, Befehle, Schematics …"),
        discord.SelectOption(label="MC Server: Survival (normal)", emoji="🌳", value="mc_survival", description="Grundstück sichern, Items verloren, Befehle, Allgemeine Fragen …"),
        discord.SelectOption(label="MC Server: Survival (Skyblock)", emoji="☁️", value="mc_skyblock", description="Items verloren, Befehle, Allgemeine Fragen …"),
        discord.SelectOption(label="MC Server: Events", emoji="🎉", value="mc_events", description="Fragen zu Community-Events und Minecraft-Gottesdiensten"),
        discord.SelectOption(label="MC Server: Bug-Report", emoji="🐛", value="mc_bugreport", description="Inhaltliche und technische Fehler und Probleme melden"),
        discord.SelectOption(label="Minecraft Launcher und Mods", emoji="💻", value="mc_launcher_mods", description="allgemeine oder technische Fragen zu Minecraft Launcher und Mods"),
        discord.SelectOption(label="Server-Beitritt / Bedrock Support", emoji="📝", value="mc_bedrock", description="Fragen und Probleme zum Server-Beitritt, Versions-Support und Bedrock-Support"),
        discord.SelectOption(label="Vor-Ort Treffen und Besuch", emoji="📍", value="meetup", description="Alles über unsere Community-Treffen, Auswärts-Termine und Besuch-Anfragen"),
        discord.SelectOption(label=LABEL_DISCORD, emoji="💬", value="discord", description="Fragen zum Discord-Server"),
        discord.SelectOption(label="Regelvertoß / Spieler melden", emoji="⚠️", value="report", description="einen Regelvertoß / Spieler melden, Streifälle, Beschwerden"),
        discord.SelectOption(label="Entbannungsantrag", emoji="🔒", value="entbannung", description="einen Entbannungsantrag stellen"),
        discord.SelectOption(label="Kooperationen", emoji="👥", value="kooperation", description="Fragen zu unseren Kooperations-Angeboten"),
        discord.SelectOption(label="Bewerbung", emoji="📚", value="bewerbung", description="Fragen zu unseren Rängen und der Bewerbung"),
        discord.SelectOption(label="Account gehackt / neuer Account", emoji="🔧", value="account", description="gehackten Account melden / Account-Daten transferieren lassen"),
        discord.SelectOption(label=LABEL_SONSTIGES, emoji="❓", value="sonstiges", description="andere Anliegen"),
    ]

    def __init__(self, ticketcog: "TicketCog"):
        super().__init__(placeholder=PLACEHOLDER_TEXT, options=self.options, custom_id="ticket_dropdown")
        self.ticketcog = ticketcog

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        logger.info(f"{interaction.user} selected `{selection}` in TicketDropdown in {interaction.channel}")

        ticket_types = {
            "mc_kreativ": {"Title": "Kreativ-Server", "message": "Bitte schildere dein Anliegen zum Kreativ-Server.", "color": 0xffaa00},
            "mc_survival": {"Title": "Survival (normal)", "message": "Bitte schildere dein Anliegen zum Survival-Server (normal).", "color": 0x007b1f},
            "mc_skyblock": {"Title": "Survival (Skyblock)", "message": "Bitte schildere dein Anliegen zum Skyblock-Server.", "color": 0x00ffbf},
            "mc_events": {"Title": "Events", "message": "Bitte schildere dein Anliegen zu Events.", "color": 0xc926ff},
            "mc_bugreport": {"Title": "Bug-Report", "message": "Bitte beschreibe den Fehler oder das Problem möglichst genau.", "color": 0x0040ff},
            "mc_launcher_mods": {"Title": "Minecraft Launcher und Mods", "message": "Bitte schildere dein Anliegen zu Launcher oder Mods.", "color": 0x6cd900},
            "mc_bedrock": {"Title": "Server-Beitritt / Bedrock Support", "message": "Bitte schildere dein Anliegen zum Server-Beitritt oder Bedrock-Support.", "color": 0x0040ff},
            "meetup": {"Title": "Vor-Ort Treffen und Besuch", "message": "Bitte schildere dein Anliegen zu Treffen oder Besuch.", "color": 0xffff00},
            "discord": {"Title": LABEL_DISCORD, "message": "Bitte schildere dein Anliegen zum Discord-Server.", "color": 0x5865f2},
            "report": {"Title": "Regelverstoß / Spieler melden", "message": "Bitte schildere den Regelverstoß oder das Problem.", "color": 0xff0000},
            "entbannung": {"Title": "Entbannungsantrag", "message": "Bitte schildere deinen Entbannungsantrag.", "color": 0x646473},
            "kooperation": {"Title": "Kooperationen", "message": "Bitte schildere dein Anliegen zu Kooperationen.", "color": 0xffff00},
            "bewerbung": {"Title": "Bewerbung", "message": "Bitte schildere dein Anliegen zur Bewerbung.", "color": 0x989898},
            "account": {"Title": "Account gehackt / neuer Account", "message": "Gehackten Account melden / Account-Daten transferieren lassen.", "color": 0xff4c4d},
            "sonstiges": {"Title": LABEL_SONSTIGES, "message": "Bitte schildere dein Anliegen.", "color": 0xffffff},
        }

        if selection in ticket_types:
            # acknowledge interaction to avoid "Unknown interaction" during long processing
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer()
            except Exception as e:
                logger.debug(f"Could not defer interaction: {e}")

            try:
                await self.ticketcog.create_ticket_thread(interaction=interaction, fields=ticket_types[selection])
            except Exception as e:
                logger.error(f"Error creating ticket thread for selection `{selection}`: {e}")
                try:
                    await interaction.followup.send("Fehler beim Erstellen des Tickets.", ephemeral=True)
                except Exception:
                    try:
                        if not interaction.response.is_done():
                            await interaction.response.send_message("Fehler beim Erstellen des Tickets.", ephemeral=True)
                    except Exception:
                        logger.debug("Failed to notify user about ticket creation error")
                return

        # restore the parent view so the original message keeps the setup UI
        parent_view = self.view
        try:
            # Try editing the original message object directly first
            try:
                await interaction.message.edit(view=parent_view)
            except Exception:
                # fallback: try editing via followup (if the interaction was deferred)
                try:
                    await interaction.followup.edit_message(message_id=interaction.message.id, view=parent_view)
                except Exception as e:
                    logger.debug(f"Could not update parent view after selection: {e}")
        except Exception as e:
            logger.debug(f"Could not update parent view after selection: {e}")

class MCServerSubSelect(discord.ui.Select):
    def __init__(self, server_type: str, ticketcog: "TicketCog"):
        self.server_type = server_type
        self.ticketcog = ticketcog

        options = []
        mapping = {}

        if server_type == "kreativ":
            options = [
                discord.SelectOption(label="Parzellen (Grundstücke)", value="grundstuecke", description="Übertragen von Parzellen, Ändern von Parzellen"),
                discord.SelectOption(label="Bau-Wettbewerbe", value="bauwettbewerbe", description="Fragen zu laufenden Bau-Wettbewerben"),
                discord.SelectOption(label="Befehle", value="befehle", description="Fragen zu speziellen Befehlen auf dem CR-Server"),
                discord.SelectOption(label="Schematics", value="schematics", description="Schematics hochladen lassen oder als Download bekommen"),
                discord.SelectOption(label="Allgemeine Fragen", value="allgemein", description="Sonstige Fragen"),
            ]

            mapping = {
                "grundstuecke": {
                    "label": "Parzellen (Grundstücke)",
                    "description": (
                        "Auf dem Kreativ-Server gibt es unterschiedliche Welten für die jeweiligen Projekte und Themen. "
                        "Manche Welten sind für jeden frei nutzbar, während andere Welten nur für bestimmte Projekte oder Gruppen gedacht sind.\n\n"
                        "🏷 **Neues Grundstück erhalten**\n"
                        "Wenn du eine neue Parzelle (= Grundstück / Plot) erhalten möchtest, kannst du dies in einer der Parzellen-Welten tun. Verwende dazu die Befehle `/warp plots` (kleine Parzellen) oder `/warp babel` (große Parzellen) und gebe dort den Befehl `/plot auto` ein.\n\n"
                        "↩️ **Auf einem Workshop-Grundstück weiterbauen**\n"
                        "Du hast bei einem Workshop oder einem Messe-Stand von uns ein Grundstück bebaut und möchtest weiterbauen? Nenne uns gerne die Plot-Koordinaten (Beispiel: `-3;10`) oder die Canstein-Nummer (Beispiel: `Canstein2`), sowie deinen privaten Minecraft-Namen. Dann können wir dir das Grundstück auf deinen Account übertragen.\n\n"
                        "Wenn du keine freien Parzellen mehr zur Verfügung hast, kannst du dich gerne hier bei uns melden. Wir können dir eine neue Parzelle geben, wenn deine bisherigen ausreichend befüllt sind.\n\n"
                        "📒 **weitere Parzellen-Befehle**\n"
                        "- `/plot home <ggf. Nummer>` - teleportiere dich zu einem deiner Parzellen\n"
                        "- `/plot visit <Spieler-Name> <ggf. Nummer>` - teleportiere dich zu einer bestimmten Parzelle eines anderen Spielers\n"
                        "- `/plot info` - zeige dir die Regions-Einstellungen deiner und fremder Parzellen an\n"
                        "- `/plot trust <Spieler-Name>` - füge einen Mitspieler zu deiner eigenen Parzelle hinzu\n"
                        "- `/plot remove <Spieler-Name>` - entferne einen (eingetragenen) Mitspieler von deiner eigenen Parzelle\n"
                        "- `/plot flag <`list`, `set`, `remove`, `add`, `info`>` - Parzellen-Einstellungen (Flags) deiner eigenen Parzelle auflisten und abändern\n\n"
                        "🏗️ **mehr Platz für größere Projekte**\n"
                        "In Ausnahmefällen können nebeneinanderliegende Parzellen auch vom Server-Team verbunden werden. Oder brauchst du für ein großes Projekt mehr Platz? Schreibe uns, was du vorhast und zeige uns gerne die Parzelle, wenn du für dieses Projekt schon etwas gebaut hast.\n\n"
                        "_Wenn du noch Fragen oder Anliegen hast, kannst du diese nun gerne hier stellen._"
                    ),
                    "color": 0xffaa00,
                },
                "bauwettbewerbe": {
                    "label": "Bau-Wettbewerbe",
                    "description": (
                        "Auf dem Server finden ab und zu Bau-Wettbewerbe zu speziellen Themen statt, für die es dann eigene Projekt-Welten mit allen Informationen und den Grundstücken gibt. Meist gehen die Bau-Wettbewerbe mehrere Monate lang. Und oft gibt es am Ende auch Preise für die besten Einsendungen zu gewinnen. Teilnehmen kann bei den Wettbewerben jeder.\n\n"
                        "**Aktuell finden jedoch keine Bau-Wettbewerbe statt.** Wenn du dennoch Fragen zu früheren oder zukünftigen Bau-Wettbewerben hast, kannst du die gerne hier stellen."
                    ),
                    "color": 0xffaa00,
                },
                "befehle": {
                    "label": "Befehle",
                    "description": (
                        "Du hast Fragen zu den Befehlen auf dem Kreativ-Server? Am Spawn (`/spawn`) befindet sich ein Banner mit den wichtigsten Befehlen für den Kreativ-Server. Ansonsten kannst du gerne hier deine Frage stellen.\n\n"
                        "> **Anmerkung:** Eine Start-Welt mit Befehlen, die auf dem gesamten Server-Netzwerk gelten, ist bereits in Planung."
                    ),
                    "color": 0x00D166,
                },
                "schematics": {
                    "label": "Schematics",
                    "description": (
                        "Ab dem Rang ‚Mitglied+‘ hast du auf dem Kreativ-Server in vielen Welten WorldEdit-Rechte. Wir bieten an, WorldEdit Schematics auf den Server hochladen zu lassen oder eigenen Bauten zum Download zur Verfügung zu stellen. Deine Schematics kannst du auf dem Server mit dem Befehl `//schem list` abfragen.\n\n"
                        "📤 **Schematic hochladen**\n"
                        "Wenn du eine Schematic auf den Server zur eigenen Verwendung hochladen möchtet, kannst du dies hier gerne anfragen. Lade dafür die Schematic-Datei hoch und schreibe, wie du in Minecraft heißt. Achte bei Schematics von anderen Leuten darauf, die Lizenzen zu beachten und die Credits entsprechend zu vergeben.\n\n"
                        "📥 **Schematics herunterladen**\n"
                        "Wenn du eines deiner Bauten als Schematic zum Download erhalten möchtest, kannst du das hier gerne anfragen. Schreibe uns dafür hier den Namen der Schematic, die du in deinem Schematic-Ordner abgespeichert hast und nenne uns deinen Minecraft-Namen."
                    ),
                    "color": 0x6cd900,
                },
                "allgemein": {
                    "label": "Allgemeine Fragen",
                    "description": "Okay. Stelle nun gerne deine Frage!",
                    "color": 0xffffff,
                },
            }

        elif server_type == "survival":
            options = [
                discord.SelectOption(label="Regions-Sicherung (Grundstück)", value="grundstueck", description="Anfragen oder Ändern einer Regions-Sicherung"),
                discord.SelectOption(label="Items / XP verloren", value="items", description="Erstattungs-Anfrage von Items / XP-Punkte"),
                discord.SelectOption(label="Befehle", value="befehle", description="Fragen zu speziellen Befehlen auf dem SV-Server"),
                discord.SelectOption(label="Role-Play", value="roleplay", description="Fragen zum Role-Play System auf dem SV-Server"),
                discord.SelectOption(label="Allgemeine Fragen", value="allgemein", description="Allgemeine Fragen"),
            ]

            mapping = {
                "grundstueck": {
                    "label": "Regions-Sicherung (Grundstück)",
                    "description": (
                        "🏷️ **Neues Grundstück**\n"
                        "Wenn du eine Stelle in der Bau-Welt gefunden hast, in dem du gerne eine Region gesichert haben möchtest, damit dein Gebautes vor anderen geschützt ist, dann kannst du dies hier gerne anfragen. Schreibe uns bitte, um welche Bau-Welt es geht (Oberwelt oder Nether). Nenne uns gerne die Block-Koordinaten der zwei gegenüberliegenden Eck-Punkte des gewünschten Grundstücks. In der Regel sichern wir die Region in der gesamten Höhe (Y-Koordinate).\n\n"
                        "> **Tipp:** Mit \"F3\" kannst du dir die Block-Koordinaten anzeigen lassen.\n\n"
                        "Schaue auch bitte, ob du genug Abstand zu Regionen / Bauten anderer Spieler hast.\n\n"
                        "🛠️ **Grundstück selber bearbeiten**\n"
                        "- `/rg info` - zeige dir die Regions-Einstellungen deiner und fremder Regionen an\n"
                        "- `/region addmember <Grundstücks-Name> <Spieler-Name>` - füge einen Mitspieler zu deiner eigenen Region hinzu\n"
                        "- `/region removemember <Grundstücks-Name> <Spieler-Name>` - entferne einen (eingetragenen) Mitspieler von deiner eigenen Region\n"
                        "- `/region flag <Grundstücks-Name> greeting <Nachricht>` - füge eine Begrüßung / Warnung / Information für den Betritt des Grundstücks hinzu\n"
                        "- `/region flag <Grundstücks-Name> farewell <Nachricht>` - füge eine Verabschiedung / Information für das Verlassen des Grundstücks hinzu\n\n"
                        "✨ **Weitere Grundstücks-Einstellungen / Flags ändern**\n"
                        "Sonderwünsche für bestimmte Einstellungen und Flags (wie beispielsweise ‚PVP‘, ‚chest-access‘ oder ‚sethome‘) kannst du hier gerne erfragen. Schreibe bitte auch, warum dies geändert werden soll. Viele Flags stellen wir nur in Ausnahmefällen um.\n\n"
                        "_Wenn du noch Fragen oder Anliegen hast, kannst du diese nun gerne hier stellen._"
                    ),
                    "color": 0x007b1f,
                },
                "items": {
                    "label": "Items / XP verloren",
                    "description": (
                        "Das Server-Team kann in bestimmten Fällen verlorene Items oder Erfahrungspunkte erstatten. Weitere Infos zur Rückerstattung findest du in unsere Minecraft Regelwerk unter §1.3 Rückerstattungen.\n\n"
                        "Kannst du bitte genau beschreiben, wann und in welcher Welt du gestorben bist oder sie verloren hast? Was ist passiert? Kannst du mit Screenshots oder sogar einer Replay-Aufnahme Beweise liefern? Das Support-Team wird sich dann ggf. intern beraten und entscheiden, ob du die Items / XPs wiederbekommst. Danke!"
                    ),
                    "color": 0x00D166,
                },
                "befehle": {
                    "label": "Befehle",
                    "description": (
                        "Du hast Fragen zu den Befehlen auf dem normalen Survival-Server? Am Spawn (`/spawn`) befinden sich im Rathaus ein paar informative Banner mit den wichtigsten Befehlen für den Survival-Server. Ebenso auch oben auf der fliegenden Starter-Insel beim Spawn. Ansonsten kannst du gerne hier deine Frage stellen.\n\n"
                        "> **Anmerkung:** Eine Start-Welt mit Befehlen, die auf dem gesamten Server-Netzwerk gelten, ist bereits in Planung."
                    ),
                    "color": 0x00D166,
                },
                "roleplay": {
                    "label": "Role-Play",
                    "description": (
                        "❔ **Allgemeine Fragen**\n"
                        "Du hast Fragen zum Role-Play System auf dem Survival-Server? Alle grundlegenden Richtlinien hierzu sind in unserem Minecraft Regelwerk beschrieben.\n\n"
                        "👥 **Neue Allianz beantragen**\n"
                        "Für die Beantragung einer neuen Allianz benötigen wir von dir den Allianznamen, den Minecraft-Namen der Leitung der Allianz und die aktuelle Anzahl der Mitglieder.\n\n"
                        "🏘️ **Neue Allianz-Region anfragen**\n"
                        "Für den Role-Play benötigt es feste Regionen, in denen dieses Spielen erlaubt ist. Hier kannst du neue Role-Play Region von uns anlegen lassen. Schreibe uns bitte - wie bei einer normalen Bau-Region auch - um welche Bau-Welt es geht (Oberwelt oder Nether). Und beschreibe den Standort oder nenne uns die gewünschten Block-Koordinaten der zwei gegenüberliegenden Eck-Punkte für die Region."
                    ),
                    "color": 0x00D166,
                },
                "allgemein": {"label": "Allgemeine Fragen", "description": "Okay. Stelle nun deine Frage oder schreibe, was du uns mitteilen möchtest!", "color": 0xffffff},
            }

        elif server_type == "skyblock":
            options = [
                discord.SelectOption(label="Items / XP verloren", value="items", description="Erstattungs-Anfrage von Items / XP-Punkte"),
                discord.SelectOption(label="Befehle", value="befehle", description="Fragen zu speziellen Befehlen auf dem Skyblock-Bereich"),
                discord.SelectOption(label="Allgemeine Fragen", value="allgemein", description="Allgemeine Fragen"),
            ]

            mapping = {
                "items": {"label": "Items / XP verloren", "description": (
                    "Das Server-Team kann in bestimmten Fällen verlorene Items oder Erfahrungspunkte erstatten. Weitere Infos zur Rückerstattung findest du in unsere Minecraft Regelwerk unter §1.3 Rückerstattungen.\n\n"
                    "Kannst du bitte genau beschreiben, wann und in welcher Welt du gestorben bist oder sie verloren hast? Was ist passiert? Kannst du mit Screenshots oder sogar einer Replay-Aufnahme Beweise liefern? Das Support-Team wird sich dann ggf. intern beraten und entscheiden, ob du die Items / XPs wiederbekommst. Danke!"
                ), "color": 0x00D166},
                "befehle": {"label": "Befehle", "description": (
                    "Du hast Fragen zu den Befehlen für den Skyblock-Bereich? Am Spawn (`/skyblock`) auf der fliegenden Starter-Insel befinden sich ein paar informative Banner mit den wichtigsten Befehlen für den Skyblock Spiel-Modus. Ansonsten kannst du gerne hier deine Frage stellen.\n\n"
                    "> **Anmerkung:** Eine Start-Welt mit Befehlen, die auf dem gesamten Server-Netzwerk gelten, ist bereits in Planung."
                ), "color": 0x00D166},
                "allgemein": {"label": "Allgemeine Fragen", "description": "Okay. Stelle nun deine Frage oder schreibe, was du uns mitteilen möchtest!", "color": 0xffffff},
            }

        elif server_type == "events":
            options = [
                discord.SelectOption(label="Allgemeine Community-Events", value="community", description="Fragen zu allgemeinen Community-Events"),
                discord.SelectOption(label="Kleine Gottesdienste (auf SV)", value="small_gottesdienst", description="Fragen zu kleinen Gottesdiensten"),
                discord.SelectOption(label="Große Gottesdienste (auf ES)", value="large_gottesdienst", description="Fragen zu großen Gottesdiensten"),
                discord.SelectOption(label="Sonstiges", value="allgemein", description="Anderes"),
            ]

            mapping = {
                "community": {"label": "Allgemeine Community-Events", "description": "Fragen zu den allgemeinen Community-Events", "color": 0xc926ff},
                "small_gottesdienst": {"label": "Kleine Gottesdienste (auf SV)", "description": "Fragen zu den kleinen Gottesdiensten auf dem SV-Server", "color": 0xc926ff},
                "large_gottesdienst": {"label": "Große Gottesdienste (auf ES)", "description": "Fragen zu den großen Gottesdiensten auf dem ES-Server", "color": 0xc926ff},
                "allgemein": {"label": "Sonstiges", "description": "Stelle nun deine Frage zum Event.", "color": 0xc926ff},
            }

        elif server_type == "meetup":
            options = [
                discord.SelectOption(label="Community-Treffen", value="community_treffen", description="Reallife-Treffen, Kirchentag etc."),
                discord.SelectOption(label="privater Bibellabor Besuch", value="privat_besuch", description="privaten Besuch vor Ort anfragen"),
                discord.SelectOption(label="eigene Veranstaltung bewerben", value="eigene_veranstaltung", description="Anfrage oder Ideen, wo wir dabei sein sollten"),
            ]

            mapping = {
                "community_treffen": {"label": "Community-Treffen", "description": "Reallife-Treffen, Kirchentag etc.\n\nWenn du Fragen zum Ablauf oder zur Teilnahme hast, schreibe sie uns hier.", "color": 0xffff00},
                "privat_besuch": {"label": "privater Bibellabor Besuch", "description": "Du möchtest unser analoges Bibellabor besuchen? Schreibe bitte Datum, ungefähre Teilnehmerzahl und Ansprechpartner sowie eine kurze Beschreibung des Anliegens.", "color": 0xffff00},
                "eigene_veranstaltung": {"label": "eigene Veranstaltung bewerben", "description": "Du möchtest uns als Mitwirkende oder Aussteller für eine Veranstaltung anfragen? Nenne uns bitte Idee, Ort und Zeitraum sowie Ansprechpartner.", "color": 0xffff00},
            }

        elif server_type == "bewerbung":
            options = [
                discord.SelectOption(label="Eventhilfe", value="eventhilfe", description="Fragen zum Eventhilfe-Rang"),
                discord.SelectOption(label="Bauhilfe / Bauhilfe+ / Bauexperte:in", value="bauhilfe", description="Fragen zu den Bau-Rängen"),
                discord.SelectOption(label="Supporthilfe / Supporter", value="supporthilfe", description="Fragen zu den Support-Rängen"),
                discord.SelectOption(label="Developerhilfe / Developer", value="developerhilfe", description="Fragen zu den Developer-Rängen"),
                discord.SelectOption(label="Administration", value="administration", description="Fragen zum Admin-Rang"),
                discord.SelectOption(label="Allgemeine Frage zu den Rängen", value="allgemein", description="Allgemeine Fragen zu den Rängen"),
            ]

            mapping = {
                "eventhilfe": {"label": "Eventhilfe", "description": "Fragen zum Eventhilfe-Rang", "color": 0x989898},
                "bauhilfe": {"label": "Bauhilfe / Bauhilfe+ / Bauexperte:in", "description": "Fragen zu den Bau-Rängen", "color": 0x989898},
                "supporthilfe": {"label": "Supporthilfe / Supporter", "description": "Fragen zu den Support-Rängen", "color": 0x989898},
                "developerhilfe": {"label": "Developerhilfe / Developer", "description": "Fragen zu den Developer-Rängen", "color": 0x989898},
                "administration": {"label": "Administration", "description": "Fragen zum Admin-Rang", "color": 0x989898},
                "allgemein": {"label": "Allgemeine Frage zu den Rängen", "description": "Stelle nun deine Frage zur Bewerbung oder den Rängen.", "color": 0x989898},
            }

        else:
            options = [discord.SelectOption(label="Allgemein", value="allgemein", description="Allgemeine Anfrage")]
            mapping = {"allgemein": {"label": "Allgemein", "description": "Bitte schildere dein Anliegen.", "color": 0xffffff}}

        super().__init__(placeholder="Bitte wähle eine Kategorie aus...", options=options, custom_id=f"{server_type}_subselect")
        self.mapping = mapping

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        data = self.mapping.get(selection)
        if data is None:
            await interaction.response.send_message("Unbekannte Kategorie.", ephemeral=True)
            return
        # Build the detailed embed for the chosen subcategory
        display_titles = {
            "kreativ": "MC Server: Kreativ-Server",
            "survival": "MC Server: Survival (normal)",
            "skyblock": "MC Server: Survival (Skyblock)",
            "events": "MC Server: Events",
            "meetup": "Vor-Ort Treffen und Besuch",
            "bewerbung": "Bewerbung",
        }
        embed_title = display_titles.get(self.server_type, "Kategorie")
        embed = discord.Embed(
            title=embed_title,
            description=data.get("description"),
            color=data.get("color", 0x00D166)
        )
        embed.set_footer(text=EMBED_FOOTER)
        embed.timestamp = discord.utils.utcnow()

        chosen_label = data.get('label')

        # Defer the interaction and then:
        # 1) try to update the main ticket overview embed to include the chosen category
        # 2) delete the setup message that contains this select view
        # 3) post the detailed embed and a clear "Gewählte Kategorie" message
        try:
            await interaction.response.defer()

            # Try to find the original ticket overview message (first bot embed with overview title)
            overview_msg = None
            async for m in interaction.channel.history(limit=50):
                if m.author == interaction.client.user and m.embeds:
                    try:
                        if m.embeds[0].title == TICKET_OVERVIEW_TITLE:
                            overview_msg = m
                            break
                    except Exception:
                        pass

            # fallback: first bot embed message
            if overview_msg is None:
                async for m in interaction.channel.history(limit=50):
                    if m.author == interaction.client.user and m.embeds:
                        overview_msg = m
                        break

            if overview_msg:
                try:
                    ov = overview_msg.embeds[0]
                    ov_dict = ov.to_dict()
                    fields = ov_dict.get('fields', [])

                    # update existing Kategorie field if present
                    updated = False
                    for f in fields:
                        if 'Kategorie' in f.get('name', ''):
                            f['value'] = f"{chosen_label} (ausgewählt von {interaction.user.display_name})"
                            updated = True
                            break

                    if not updated:
                        fields.append({
                            'name': '🗂️ Gewählte Kategorie',
                            'value': f"{chosen_label} (ausgewählt von {interaction.user.display_name})",
                            'inline': False
                        })

                    ov_dict['fields'] = fields
                    new_embed = discord.Embed.from_dict(ov_dict)
                    await overview_msg.edit(embed=new_embed)
                except Exception as e:
                    logger.debug(f"Could not update overview embed with chosen category: {e}")

            # delete the setup message (the one that contains this select view)
            try:
                await interaction.message.delete()
            except Exception as e:
                logger.debug(f"Failed to delete setup message: {e}")

            # finally send the detailed embed and a clear selection message
            await interaction.followup.send(content=f"**Gewählte Kategorie:** {chosen_label}\n\nDanke. Stelle nun deine Frage oder schreibe, was du uns mitteilen möchtest!", embed=embed)

        except Exception as e:
            logger.exception(f"Error handling subselect callback: {e}")
            try:
                await interaction.followup.send("Fehler beim Verarbeiten der Auswahl.", ephemeral=True)
            except:
                pass

class MCServerSetupView(discord.ui.View):
    def __init__(self, ticketcog: "TicketCog", server_type: str):
        super().__init__(timeout=None)
        self.ticketcog = ticketcog
        self.server_type = server_type
        self.add_item(MCServerSubSelect(server_type, ticketcog))

class RenameThread():
    def __init__(self):
        pass
    
    async def show_rename_modal(self, interaction: discord.Interaction):
        modal = RenameThreadModal()
        await interaction.response.send_modal(modal)

# The private / mod Ticket menu.
class TicketModMenu(View):
    def __init__(self, *, bot, timeout = 200, ticketcog: "TicketCog"):
        super().__init__(timeout=timeout)
        self.ticketcog = ticketcog
        self.bot = bot
        
        close_btn = Button(emoji=LOCK_EMOJI, label="Ticket schließen", style=DANGER)
        lock_btn = Button(emoji="🔐", label="Thread sperren", style=PURPLE)
        rename_btn = Button(emoji="✏️", label="Ticket umbenennen", style=SECONDARY)
        trans_btn = Button(emoji=TRANSCRIPT_EMOJI, label="Transkript", style=SECONDARY)
        archive_btn = Button(emoji=ARCHIVE_EMOJI, label="Archivieren", style=SECONDARY)
        delete_btn = Button(emoji=TRASHCAN_EMOJI, label="Löschen", style=DANGER)

        close_btn.callback = self.close_callback
        lock_btn.callback = self.lock_callback
        rename_btn.callback = self.rename_callback
        trans_btn.callback = self.trans_callback
        archive_btn.callback = self.archive_callback
        delete_btn.callback = self.delete_callback

        self.add_item(close_btn)
        self.add_item(lock_btn)
        self.add_item(rename_btn)
        self.add_item(trans_btn)
        self.add_item(archive_btn)
        self.add_item(delete_btn)
        
    async def trans_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TransDesc(bot=self.bot))
        
    async def archive_callback(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} clicked archive in {interaction.channel}")
        if not (
            interaction.user.guild_permissions.administrator or
            any(role.name in [MOD, TRAIL_MOD] for role in interaction.user.roles)
        ):
            logger.warning(f"{interaction.user} tried to archive ticket without permission in {interaction.channel}")
            embed = discord.Embed(
                title="❌ Keine Berechtigung",
                description=NO_PERMISSION,
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Use the existing archive modal which allows renaming and archiving
        await interaction.response.send_modal(ThreadModalRename())

    async def delete_callback(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} clicked delete in {interaction.channel}")
        if not (
            interaction.user.guild_permissions.administrator or
            any(role.name in [MOD, TRAIL_MOD] for role in interaction.user.roles)
        ):
            logger.warning(f"{interaction.user} tried to delete ticket without permission in {interaction.channel}")
            embed = discord.Embed(
                title="❌ Keine Berechtigung",
                description=NO_PERMISSION,
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="🗑️ Ticket löschen",
            description=f"{interaction.user.mention} Möchtest du dieses Ticket wirklich löschen?",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, view=DeleteConfirmView(ticketcog=self.ticketcog), ephemeral=True)
        
    async def close_callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔒 Ticket wird geschlossen",
            description=f"Schließe das Ticket {LOADING_EMOJI}",
            color=0xffa500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=5)
        await closeTicket(self, interaction=interaction)
        
    async def lock_callback(self, interaction):
        await interaction.channel.edit(locked=True)
        embed = discord.Embed(
            title="🔐 Thread gesperrt",
            description=f"Thread locked by {interaction.user.mention}",
            color=0x800080
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    async def rename_callback(self, interaction):
        rename_thread = RenameThread()
        await rename_thread.show_rename_modal(interaction)