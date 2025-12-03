import discord

def simple_embed(text: str, thumbnail: str | None = None, color: int = 0x00ff00):
    embed = discord.Embed(description=text, color=color)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    return embed