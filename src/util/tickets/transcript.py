# ruff: noqa: F403 F405
import discord
from jinja2 import Environment, FileSystemLoader
import io
import markdown
from util.constants import *
from modals.ticketmodals import *
from util.tickets.ticket_creator import get_ticket_creator, get_ticket_users
from collections import Counter
from lang.texts import *
import re

EMOJI_PATTERN = re.compile(r'<(a?):([^:]+):(\d+)>')
URL_PATTERN = re.compile(r'(https?://\S+)')

async def trans_ticket(interaction: discord.Interaction, summary: str, bot):
    guild = interaction.guild
    TICKET_CREATOR_ID = get_ticket_creator(interaction.channel.id)
    
    if TICKET_CREATOR_ID is None:
        error_embed = discord.Embed(
            title=f"{ERROR}",
            description="Error, member wurde nicht gefunden.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    TICKET_CREATOR = guild.get_member(TICKET_CREATOR_ID)
    
    if not any(role.name in [MOD, TRAIL_MOD] for role in interaction.user.roles):
        permission_embed = discord.Embed(
            title=f"{NO_PERMISSION_TITLE}",
            description=f"{NO_PERMISSION}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=permission_embed, ephemeral=True, delete_after=10)
        return

    loading_embed = discord.Embed(
        title=f"{TRANSCRIPT_EMOJI} Transkript wird erstellt",
        description=f"Erstelle das Transkript {LOADING_EMOJI}",
        color=0xffff00
    )
    await interaction.response.send_message(embed=loading_embed)

    channel = interaction.channel
    render_messages = []
    message_count = 0
    user_message_counts = Counter()

    async for msg in channel.history(limit=None):
        if not msg.clean_content and not msg.embeds and not msg.attachments:
            continue
            
        if not msg.author.bot:
            message_count += 1
            user_message_counts[msg.author.name] += 1

        embed_data = []
        for e in msg.embeds:
            processed_fields = [
                {
                    "name": markdown.markdown(field.name) if field.name else "",
                    "value": markdown.markdown(field.value) if field.value else "",
                    "inline": field.inline
                }
                for field in e.fields
            ]
            
            embed_dict = {
                "title": markdown.markdown(e.title) if e.title else None,
                "description": markdown.markdown(e.description) if e.description else None,
                "color": f"#{e.color.value:06x}" if e.color else "#4f545c",
                "image_url": e.image.url if e.image else None,
                "thumbnail_url": e.thumbnail.url if e.thumbnail else None,
                "fields": processed_fields
            }
            embed_data.append(embed_dict)

        content = _process_message_content(msg.clean_content)
        
        attachments = [
            att.url for att in msg.attachments
            if att.content_type and att.content_type.startswith("image/")
        ]

        render_messages.append({
            "author_name": msg.author.display_name,
            "avatar_url": msg.author.display_avatar.url,
            "timestamp": msg.created_at.strftime('%d-%m-%Y %H:%M'),
            "content": content,
            "attachments": attachments,
            "embeds": embed_data
        })

    render_messages.reverse()

    env = Environment(loader=FileSystemLoader('.'))
    try:
        template = env.get_template('src/util/transcript_template.html')
    except FileNotFoundError:
        file_error_embed = discord.Embed(
            title=f"{ERROR}",
            description=f"Die Datei 'transcript_template.html' wurde nicht gefunden.",
            color=0xff0000
        )
        await interaction.edit_original_response(embed=file_error_embed)
        return

    rendered_html = template.render(
        channel_name=channel.name,
        messages=render_messages
    )

    users = await get_ticket_users(interaction.channel)
    member_count = len([user for user in users if not user.bot])

    buffer = io.BytesIO(rendered_html.encode())
    transcript_file = discord.File(buffer, filename=f"transcript von {channel.name}.html")
    
    trans_channel = bot.get_channel(int(TRANS_CHANNEL_ID))
    
    embed = _create_transcript_embed(
        channel, TICKET_CREATOR, summary, message_count, 
        member_count, user_message_counts, interaction.user
    )
    
    transcript_message = await trans_channel.send(embed=embed, file=transcript_file)
    
    success_embed = discord.Embed(
        title=f"{TRANSCRIPT_EMOJI} Transkript erstellt",
        description=f"Transkript wurde in {trans_channel.mention} erstellt!\n[Zum Transkript]({transcript_message.jump_url})",
        color=0x00ff00
    )
    await interaction.edit_original_response(embed=success_embed)

def _process_message_content(content):
    content = URL_PATTERN.sub(r'<a href="\1" target="_blank">\1</a>', content)
    
    def replace_emoji(match):
        animated = match.group(1) == 'a'
        name = match.group(2)
        emoji_id = match.group(3)
        ext = 'gif' if animated else 'png'
        emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
        return f'<img src="{emoji_url}" alt=":{name}:" title=":{name}:" class="emoji" width="22" height="22">'
    
    content = EMOJI_PATTERN.sub(replace_emoji, content)
    return markdown.markdown(content)

def _create_transcript_embed(channel, ticket_creator, summary, message_count, 
                           member_count, user_message_counts, interaction_user):
    user_message_count_str = "\n".join(
        f"* {user} ({count})" for user, count in user_message_counts.items()
    )
    
    embed = discord.Embed(
        title=f"{TRANSCRIPT_EMOJI} Transkript - {channel.name}",
        description="**Stats**",
        color=0x00ff00
    )
    
    if ticket_creator:
        embed.set_author(name=ticket_creator, icon_url=ticket_creator.avatar.url)
    
    embed.add_field(name="Beschreibung", value=summary or "Keine Beschreibung gegeben.", inline=False)
    embed.add_field(name="Nachrichten", value=message_count, inline=True)
    embed.add_field(name="Erstellt von", value=ticket_creator or "Unbekannt", inline=True)
    embed.add_field(name=f"Benutzer (Insgesamt: {member_count})", value=user_message_count_str, inline=False)
    embed.set_thumbnail(url=interaction_user.avatar.url)
    embed.set_footer(text=EMBED_FOOTER)
    embed.timestamp = discord.utils.utcnow()
    
    return embed
