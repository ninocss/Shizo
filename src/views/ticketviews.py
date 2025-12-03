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

async def closeTicket(self, interaction: discord.Interaction):
    guild = interaction.guild
    TICKET_CREATOR_ID = get_ticket_creator(interaction.channel.id) 
    if TICKET_CREATOR_ID is None:
        logger.warning(f"Ticket creator ID not found for channel {interaction.channel.id}")
        embed = discord.Embed(
            title=f"{ERROR}",
            description="Member wurde nicht gefunden.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    TICKET_CREATOR = guild.get_member(TICKET_CREATOR_ID)

    if TICKET_CREATOR is None:
        logger.warning(f"Ticket creator not found in guild for ID {TICKET_CREATOR_ID}")
        embed = discord.Embed(
            title=f"{ERROR}",
            description="Member wurde nicht gefunden.",
            color=0xff0000
        )
        
    for member in interaction.channel.members:
        guild_member = guild.get_member(member.id)
        if guild_member is None:
            continue
            
        has_required_role = any(role.name in [TEAM_ROLE, MOD, TRAIL_MOD] for role in guild_member.roles)

        if not has_required_role:
            logger.info(f"Removing user {guild_member} from ticket channel {interaction.channel}")
            await interaction.channel.remove_user(guild_member)
            await asyncio.sleep(0.5)

            if SEND_TICKET_FEEDBACK is True:                
                embed = discord.Embed(
                    title=f"{LOCK_EMOJI} Ticket geschlossen - {interaction.channel.name}",
                    description=f"**Geschlossen von:** {interaction.user.mention}\n**Grund:** Keine Angabe\n**Server:** {interaction.guild.name}",
                    color=0xff0000
                )
                embed.set_thumbnail(url=interaction.guild.icon)
                embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
                embed.set_footer(text=EMBED_FOOTER)
                embed.timestamp = discord.utils.utcnow()
                logger.info(f"Sending closed ticket embed to {guild_member}")
                await guild_member.send(embed=embed)
        else:
            logger.debug(f"User {guild_member} has required role, not removing from ticket channel")
        
    if not interaction.channel.name.startswith("[CLOSED] "):
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
                description="I couldn't find any songs in the recent history.",
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
                description="I couldn't find any songs in the recent history.",
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
        logger.info(f"{interaction.user} confirmed closing ticket with reason '{self.reason}' in {interaction.channel}")
        await interaction.message.delete()
        global DELETE_USER
        DELETE_USER = interaction.user
        reason = self.reason
        
        guild = interaction.guild
        TICKET_CREATOR_ID = get_ticket_creator(interaction.channel.id) 
        
        if TICKET_CREATOR_ID is None:
            logger.warning(f"Ticket creator ID not found for channel {interaction.channel.id}")
            pass

        TICKET_CREATOR = guild.get_member(TICKET_CREATOR_ID)

        if TICKET_CREATOR is None:
            logger.warning(f"Ticket creator not found in guild for ID {TICKET_CREATOR_ID}")
            pass
        
        embed = discord.Embed(
            title=f"{LOCK_EMOJI} Ticket geschlossen - {interaction.channel.name}",
            description=f"**Geschlossen von:** {interaction.user.mention}\n**Grund:** {reason}\n**Server:** {interaction.guild.name}",
            color=0xff0000
        )
        embed.set_thumbnail(url=interaction.guild.icon)
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.set_footer(text=EMBED_FOOTER)
        embed.timestamp = discord.utils.utcnow()
        
        for member in interaction.channel.members:
            guild_member = guild.get_member(member.id)
            logger.info(f"trying to remove users: {guild_member}")
            has_required_role = any(role.name in [TEAM_ROLE, MOD, TRAIL_MOD] for role in guild_member.roles)

            if not has_required_role:
                logger.info(f"Removing user {guild_member} from ticket channel {interaction.channel}")
                await interaction.channel.remove_user(guild_member)
                await asyncio.sleep(0.5)
                
                if SEND_TICKET_FEEDBACK is True:
                    logger.info(f"Sending closed ticket embed to {guild_member}")
                    await guild_member.send(embed=embed)
            else:
                logger.debug(f"User {guild_member} has required role, not removing from ticket channel")
            
        if not interaction.channel.name.startswith("[CLOSED] "):
            close_embed = discord.Embed(
                title="🔒 Ticket geschlossen",
                description=f"Ticket geschlossen von {interaction.user.mention} aus folgendem Grund:\n```{reason}```",
                color=0xff0000
            )
            close_embed.add_field(
                name="📊 Ticket Information",
                value=f"**Channel:** {interaction.channel.name}\n**Closed at:** <t:{int(discord.utils.utcnow().timestamp())}:F>\n**Channel ID:** {interaction.channel.id}",
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
            message_authors = set()
            try:
                async for message in interaction.channel.history(limit=None):
                    if message.author.id != self.bot.user.id:
                        message_authors.add(message.author.id)
            except:
                pass
            
            for member in interaction.channel.members:
                guild_member = guild.get_member(member.id)
                if (guild_member and 
                    any(role.name in [TEAM_ROLE, MOD, TRAIL_MOD] for role in guild_member.roles) and
                    guild_member.id in message_authors):
                    support_members.append(guild_member)
            
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

                close_embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
                close_embed.set_footer(text=f"{EMBED_FOOTER}", icon_url=interaction.user.display_avatar.url)
                close_embed.timestamp = discord.utils.utcnow()
                
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
                description="Alle setup Nachrichten im Ticket wurden gelöscht.",
                color=0x00ff00
                )
                await interaction.followup.send_message(embed=embed, ephemeral=True, delete_after=20)
                
                await asyncio.sleep(0.5)
                await interaction.channel.add_user(TICKET_CREATOR)
                
                reopen_embed = discord.Embed(
                title="🔓 Ticket neu eröffnet",
                description=f"{TICKET_CREATOR.mention} Das Ticket wurde neu eröffnet.",
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

# The ticket-setup view
class TicketSetupView(View):
    def __init__(self, ticketcog: "TicketCog"):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown(ticketcog))

# The ticket-setup view dropdown
class TicketDropdown(discord.ui.Select):
    options = [
        discord.SelectOption(label=LABEL_DISCORD, emoji="💬", value="discord"),
        discord.SelectOption(label=LABEL_MINECRAFT, emoji="⛏️", value="minecraft"),
        discord.SelectOption(label=LABEL_BEREICH, emoji="🚧", value="bereich"),
        discord.SelectOption(label=LABEL_PARZELLE, emoji="🛠️", value="parzelle"),
        discord.SelectOption(label=LABEL_ENTBANNUNG, emoji="📝", value="entbannung"),
        discord.SelectOption(label=LABEL_SONSTIGES, emoji="❓", value="sonstiges")
    ]
    
    def __init__(self, ticketcog: "TicketCog"):
        super().__init__(placeholder=PLACEHOLDER_TEXT, options=self.options, custom_id="ticket_dropdown")
        self.ticketcog = ticketcog
        
    async def callback(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} selected '{self.values[0]}' in TicketDropdown in {interaction.channel}")
        
        parent_view = self.view
        self.placeholder = PLACEHOLDER_TEXT
        
        if self.values[0] == "discord":
            fields = {
                "Title": TITLE_DISCORD,
                "message": MESSAGE_GENERAL
            }
            
            await self.ticketcog.create_ticket_thread(interaction=interaction, fields=fields)
            
        elif self.values[0] == "minecraft":
            fields = {
                "Title": TITLE_MINECRAFT,
                "message": MESSAGE_GENERAL
            }
            await self.ticketcog.create_ticket_thread(interaction=interaction, fields=fields)
            
        elif self.values[0] == "entbannung":       
            fields = {
                "Title": TITLE_ENTBANNUNG,
                "message": MESSAGE_ENTBANNUNG
            }
            await self.ticketcog.create_ticket_thread(interaction=interaction, fields=fields)
            
        elif self.values[0] == "bereich":
            await interaction.response.send_modal(bereichModal(ticketcog=self.ticketcog))
            
        elif self.values[0] == "parzelle":
            await interaction.response.send_modal(parzelleModal(ticketcog=self.ticketcog))
            
        elif self.values[0] == "sonstiges":
            fields = {
                "Title": TITLE_SONSTIGES,
                "message": MESSAGE_GENERAL
            }
            await self.ticketcog.create_ticket_thread(interaction=interaction, fields=fields)
        
        if interaction.response.is_done():
            await interaction.followup.edit_message(message_id=interaction.message.id, view=parent_view)
        else: 
            await interaction.response.edit_message(view=parent_view)

# The delete confirmation view
class DeleteConfirmView(View):
    def __init__(self, *, timeout = 180, ticketcog: "TicketCog"):
        super().__init__(timeout=timeout)
        self.ticketcog = ticketcog
        
        yes_button = Button(emoji=CHECK, style=DANGER, label="Ja, löschen")
        yes_button.callback = self.yes_button
        
        no_button = Button(emoji=UNCHECK, style=SECONDARY, label="Nein")
        no_button.callback = self.no_button
        
        self.add_item(yes_button)
        self.add_item(no_button)
        
    async def yes_button(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🗑️ Deleting Ticket",
            description=f"This ticket is being deleted {LOADING_EMOJI}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed)
        logger.info(f"{interaction.user} confirmed deleting ticket in {interaction.channel}")
        delete_ticket_creator(interaction.channel.id)
        await interaction.channel.delete()
        
    async def no_button(self, interaction: discord.Interaction):
        logger.info(f"{interaction.user} cancelled deleting ticket in {interaction.channel}")
        await interaction.message.delete()

class RenameThreadModal(discord.ui.Modal, title="Rename Thread"):
    def __init__(self):
        super().__init__()
        
    name_input = discord.ui.TextInput(
        label="New Thread Name",
        placeholder="Enter the new name for this thread...",
        max_length=100,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        new_name = self.name_input.value.strip()
        
        if not new_name:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Thread name cannot be empty!",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        try:
            await interaction.channel.edit(name=new_name)
            logger.info(f"Thread renamed to '{new_name}' by {interaction.user} in {interaction.channel}")
            embed = discord.Embed(
                title="✅ Thread umbenannt",
                description=f"Thread renamed to: **{new_name}**",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.HTTPException as e:
            logger.error(f"Failed to rename thread: {e}")
            embed = discord.Embed(
                title="❌ Fehler",
                description=f"Failed to rename thread: {str(e)}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

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
        
        close_btn = Button(emoji=LOCK_EMOJI, label="Close Ticket", style=DANGER)
        lock_btn = Button(emoji="🔐", label="Lock Ticket", style=PURPLE)
        rename_btn = Button(emoji="✏️", label="Rename Ticket", style=SECONDARY)
        trans_btn = Button(emoji=TRANSCRIPT_EMOJI, label="Transcript Ticket", style=SECONDARY)
        
        close_btn.callback = self.close_callback
        lock_btn.callback = self.lock_callback
        rename_btn.callback = self.rename_callback
        trans_btn.callback = self.trans_callback
        
        self.add_item(close_btn)
        self.add_item(lock_btn)
        self.add_item(rename_btn)
        self.add_item(trans_btn)
        
    async def trans_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TransDesc(bot=self.bot))
        
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