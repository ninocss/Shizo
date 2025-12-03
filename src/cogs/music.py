# ruff: noqa: F403 F405
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import random
import concurrent.futures
from typing import List, Optional, Tuple
from util.constants import *
from util.music.queue import *
from modals.embeds import *
from lang.texts import *
from views.ticketviews import ActionsView
import json
import os
from datetime import datetime, timedelta
from ytmusicapi import YTMusic
import re

guild_queues = {}

def safe_avatar(user: discord.abc.User) -> Optional[str]:
    try:
        return user.display_avatar.url
    except Exception:
        return None

class AsyncSongLoader:
    def __init__(self, max_workers=4):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    async def extract_info_async(self, url: str, loop=None):
        if loop is None:
            loop = asyncio.get_running_loop()

        def run_yt():
            with yt_dlp.YoutubeDL(YT_OPTS) as ydl:
                return ydl.extract_info(url, download=False)

        return await loop.run_in_executor(self.executor, run_yt)

    async def preload_audio_source(self, stream_url: str, loop=None):
        if loop is None:
            loop = asyncio.get_running_loop()

        def create_source():
            ffmpeg_args = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn -bufsize 512k'
            }
            return discord.FFmpegOpusAudio(stream_url, **ffmpeg_args)

        return await loop.run_in_executor(self.executor, create_source)

song_loader = AsyncSongLoader()

class OptimizedQueue:
    def __init__(self):
        self.queue: List[Tuple[discord.AudioSource, tuple]] = []
        self.playing = False
        self.lock = asyncio.Lock()

    def add(self, song_data):
        self.queue.append(song_data)

    def get_next(self):
        if self.queue:
            return self.queue.pop(0)
        return None

    def peek(self):
        return self.queue[0] if self.queue else None

    def is_empty(self):
        return len(self.queue) == 0

    def clear(self):
        self.queue.clear()

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.background_tasks = set()

    def make_embed(
        self,
        title: str,
        description: Optional[str] = None,
        *,
        color: int = 0x5865F2,
        thumbnail: Optional[str] = None,
        author_name: Optional[str] = None,
        author_icon: Optional[str] = None,
        footer: Optional[str] = None,
        footer_icon: Optional[str] = None,
        fields: Optional[List[Tuple[str, str, bool]]] = None,
    ) -> discord.Embed:
        embed = discord.Embed(title=title, description=description or "", color=color)
        embed.timestamp = discord.utils.utcnow()
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if author_name:
            embed.set_author(name=author_name, icon_url=author_icon or discord.Embed.Empty)
        if footer:
            embed.set_footer(text=footer, icon_url=footer_icon or discord.Embed.Empty)
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        return embed

    def create_background_task(self, coro):
        task = asyncio.create_task(coro)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        return task

    async def send_static_message(self):
        try:
            actions_embed = self.make_embed(
                title="Music Controls",
                description="Use the commands below to control music.",
                color=0x5865F2,
                thumbnail=safe_avatar(self.bot.user),
                footer=f"Serving {len(self.bot.users)} users",
                footer_icon=safe_avatar(self.bot.user),
                fields=[
                    ("Commands",
                     "```\n/play <url|search>\n/queue\n/skip\n/pause\n/shuffle\n/stop\n/chart\n/clearqueue\n```",
                     False),
                    ("Status",
                     f"```\nServers: {len(self.bot.guilds)}\nUsers: {len(self.bot.users)}\n```",
                     True)
                ]
            )

            channel = await self.bot.fetch_channel(I_CHANNEL)
            if channel:
                async for message in channel.history(limit=100):
                    if (
                        message.author == self.bot.user and
                        message.embeds and
                        message.embeds[0].title and
                        "Music Controls" in message.embeds[0].title
                    ):
                        await message.delete()
                        break

                await channel.send(embed=actions_embed, view=ActionsView(bot=self.bot))
        except Exception as e:
            print(f"Error sending disconnect message: {e}")

    async def play_next(self, guild, voice_client, interaction):
        if guild.id not in guild_queues:
            return

        queue = guild_queues[guild.id]
        next_song_data = queue.get_next()

        if next_song_data:
            try:
                webpage_url = next_song_data['song_url']
                
                fresh_info = await song_loader.extract_info_async(webpage_url)
                
                if not fresh_info or "url" not in fresh_info:
                    print(f"Failed to get fresh stream URL for {webpage_url}")
                    queue.playing = False
                    await self.play_next(guild, voice_client, interaction)
                    return
                
                stream_url = fresh_info["url"]
                
                source = await song_loader.preload_audio_source(stream_url)
                
            except Exception as e:
                print(f"Error creating audio source: {e}")
                queue.playing = False
                await self.play_next(guild, voice_client, interaction)
                return

            queue.playing = True

            def after_song(e):
                if e:
                    print(f"Playback error: {e}")
                queue.playing = False
                pn = self.play_next(guild, voice_client, interaction)
                asyncio.run_coroutine_threadsafe(pn, self.bot.loop)

            try:
                voice_client.play(source, after=after_song)
            except Exception as e:
                print(f"Error starting playback: {e}")
                queue.playing = False
                return

            metadata = (
                next_song_data['title'],
                next_song_data['thumbnail'],
                None,
                next_song_data['duration'],
                next_song_data['author'],
                next_song_data['song_url'],
                next_song_data['likes'],
                next_song_data['views'],
                next_song_data['upload_date']
            )
            
            embed = self.create_now_playing_embed(metadata, interaction)
            try:
                msg = await interaction.channel.send(embed=embed)
                self.create_background_task(
                    self.update_progress(msg, embed, next_song_data['duration'])
                )
            except Exception as e:
                print(f"Error sending now playing message: {e}")
        elif AUTO_PLAY_ENABLED:
            print("autoplaying")
            song_link = None

            channel = getattr(interaction, "channel", None) or await self.bot.fetch_channel(I_CHANNEL)
            try:
                async for msg in channel.history(limit=200):
                    if not msg.embeds:
                        continue
                    for emb in msg.embeds:
                        candidates = []
                        if getattr(emb, "url", None):
                            candidates.append(emb.url)
                        if getattr(emb, "title", None):
                            candidates.append(emb.title)
                        if getattr(emb, "description", None):
                            candidates.append(emb.description)
                        if getattr(emb, "fields", None):
                            for f in emb.fields:
                                candidates.append(f.name)
                                candidates.append(f.value)

                        url_re = re.compile(r"(https?://(?:music\.youtube\.com|(?:www\.)?youtube\.com|youtu\.be)[^\s]+)", re.IGNORECASE)
                        for text in candidates:
                            if not text:
                                continue
                            m = url_re.search(text)
                            if m:
                                song_link = m.group(1)
                                break
                        if song_link:
                            break
                    if song_link:
                        break
            except Exception as e:
                print(f"Error scanning history for embed song link: {e}")
            
            try: 
                fresh_info = await song_loader.extract_info_async(song_link)
                if not fresh_info or "url" not in fresh_info:
                    print(f"Failed to get fresh stream URL for autoplay {song_link}")
                    queue.playing = False
                    return

                stream_url = fresh_info["url"]
                source = await song_loader.preload_audio_source(stream_url)
            except Exception as e:
                print(f"Error creating audio source for autoplay: {e}")
                queue.playing = False
                return
            
            try:
                print("suggestions")
                yt = YTMusic()
                video_id_match = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", song_link)
                if not video_id_match:
                    print(f"Could not extract video ID from link: {song_link}")
                    return

                video_id = video_id_match.group(1)
                related_songs = yt.get_song_related(video_id)

                suggestion = related_songs[0]["videoid"]

                try:
                    webpage_url = f"https://www.youtube.com/watch?v={suggestion}"
                    
                    fresh_info = await song_loader.extract_info_async(webpage_url)
                    
                    if not fresh_info or "url" not in fresh_info:
                        print(f"Failed to get fresh stream URL for {webpage_url}")
                        queue.playing = False
                        await self.play_next(guild, voice_client, interaction)
                        return
                    
                    stream_url = fresh_info["url"]
                    
                    source = await song_loader.preload_audio_source(stream_url)
                    
                except Exception as e:
                    print(f"Error creating audio source: {e}")
                    queue.playing = False
                    await self.play_next(guild, voice_client, interaction)
                    return
                
                queue.playing = True

                def after_song(e):
                    if e:
                        print(f"Playback error: {e}")
                    queue.playing = False
                    pn = self.play_next(guild, voice_client, interaction)
                    asyncio.run_coroutine_threadsafe(pn, self.bot.loop)

                try:
                    voice_client.play(source, after=after_song)
                except Exception as e:
                    print(f"Error starting playback: {e}")
                    queue.playing = False
                    return

                metadata = (
                    next_song_data['title'],
                    next_song_data['thumbnail'],
                    None,
                    next_song_data['duration'],
                    next_song_data['author'],
                    next_song_data['song_url'],
                    next_song_data['likes'],
                    next_song_data['views'],
                    next_song_data['upload_date']
                )
                
                embed = self.create_now_playing_embed(metadata, interaction)
                try:
                    msg = await interaction.channel.send(embed=embed)
                    self.create_background_task(
                        self.update_progress(msg, embed, next_song_data['duration'])
                    )
                except Exception as e:
                    print(f"Error sending now playing message: {e}")
            except Exception as e:
                print(f"Autoplay error: {e}")

        else:
            print("queue stopped")
            queue.playing = False

    def create_now_playing_embed(self, metadata, interaction):
        title, thumbnail, _, duration, author, song_url, likes, views, upload_date = metadata

        def format_time(seconds):
            m, s = divmod(int(seconds), 60)
            return f"{m:02}:{s:02}"

        fields = [
            ("Artist", f"{author}", True),
            ("Duration", f"{format_time(duration)}", True),
            ("Link", f"{song_url}", True),
        ]

        embed = self.make_embed(
            title="Now playing",
            description=title,
            color=0x5865F2,
            thumbnail=thumbnail,
            author_name=f"Requested by {interaction.user.display_name}",
            author_icon=safe_avatar(interaction.user),
            footer="Use /skip to go to the next song",
            footer_icon=safe_avatar(self.bot.user),
            fields=[(n, f"```\n{v}\n```", True) for n, v, _ in fields]
        )
        return embed

    async def update_progress(self, message, embed, duration):
        try:
            await asyncio.sleep(max(0, int(duration)))
            embed.color = 0x95a5a6
            embed.set_footer(text="Playback finished", icon_url=safe_avatar(self.bot.user))
            await message.edit(embed=embed)
        except (discord.HTTPException, asyncio.CancelledError):
            pass

    def format_time(self, seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m:02}:{s:02}"

    async def process_single_entry(self, entry: dict):
        try:
            if not entry or "url" not in entry:
                print(f"Error processing entry: Missing 'url' key")
                return None

            return {
                'entry_data': entry,
                'title': entry.get("title", "Unknown title"),
                'thumbnail': entry.get("thumbnail"),
                'duration': entry.get("duration", 0),
                'author': entry.get("uploader", "Unknown author"),
                'song_url': entry.get("webpage_url", "Unknown URL"),
                'likes': entry.get("like_count", 0),
                'views': entry.get("view_count", 0),
                'upload_date': entry.get("upload_date", "Unknown date")
            }

        except Exception as e:
            print(f"Error processing entry: {e}")
            return None

    async def process_song_entries(self, entries: List[dict], guild_id: int):
        if guild_id not in guild_queues:
            guild_queues[guild_id] = OptimizedQueue()

        queue = guild_queues[guild_id]
        processed_songs = []

        batch_size = 5
        for i in range(0, len(entries), batch_size):
            batch = entries[i:i + batch_size]

            tasks = []
            for entry in batch:
                if entry:
                    tasks.append(self.process_single_entry(entry))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception) or not result:
                        continue
                    processed_songs.append(result)
                    queue.add(result)

        return processed_songs

    @app_commands.command(name="chart", description="Plays a random song from the YouTube Music charts")
    async def play_chart(self, interaction: discord.Interaction):
        if await self.check_timeout_decorator(interaction):
            return
        else:
            await interaction.response.defer()

        loading_embed = self.make_embed(
            title="Loading chart",
            description="Fetching popular songs...",
            color=0x3498db,
        )

        loading_message = await interaction.followup.send(embed=loading_embed)

        try:
            chart_urls = [
                "https://music.youtube.com/playlist?list=RDCLAK5uy_kmPRjHDECIcuVwnKsx5w4UBCp9jSEMzM",
                "https://music.youtube.com/playlist?list=RDCLAK5uy_k8jhb5wP3rUqLOWFzVQNE_YdIcF7O4BN",
                "https://www.youtube.com/playlist?list=PLFgquLnL59alCl_2TQvOiD5Vgm1hCaGSI",
            ]

            playlist_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'playlist_items': '1-20',
            }

            trending_songs = []

            for chart_url in chart_urls:
                try:
                    def extract_playlist_info():
                        with yt_dlp.YoutubeDL(playlist_opts) as ydl:
                            return ydl.extract_info(chart_url, download=False)

                    chart_info = await asyncio.get_running_loop().run_in_executor(
                        song_loader.executor, extract_playlist_info
                    )

                    if "entries" in chart_info and chart_info["entries"]:
                        for entry in chart_info["entries"][:15]:
                            if entry and entry.get("title"):
                                title = entry["title"]
                                uploader = entry.get("uploader", "")
                                if uploader and uploader.lower() not in title.lower():
                                    song_query = f"{title} {uploader}"
                                else:
                                    song_query = title
                                trending_songs.append(song_query)

                        if trending_songs:
                            break

                except Exception as e:
                    print(f"Fehler beim Laden der Playlist {chart_url}: {e}")
                    continue

            if not trending_songs:
                try:
                    search_queries = [
                        "ytsearch5:music charts 2024",
                        "ytsearch5:trending music now",
                        "ytsearch5:top songs 2024"
                    ]

                    for search_query in search_queries:
                        try:
                            search_results = await song_loader.extract_info_async(search_query)
                            if "entries" in search_results:
                                for entry in search_results["entries"][:5]:
                                    if entry and entry.get("title"):
                                        title = entry["title"]
                                        uploader = entry.get("uploader", "")
                                        if uploader and uploader.lower() not in title.lower():
                                            song_query = f"{title} {uploader}"
                                        else:
                                            song_query = title
                                        trending_songs.append(song_query)

                                if trending_songs:
                                    break
                        except Exception as e:
                            print(f"Fehler bei der Suche {search_query}: {e}")
                            continue

                except Exception as e:
                    print(f"Fehler bei der Fallback-Suche: {e}")

            if not trending_songs:
                trending_songs = [
                    "Flowers Miley Cyrus",
                    "As It Was Harry Styles",
                    "Bad Habit Steve Lacy",
                    "About Damn Time Lizzo",
                    "Heat Waves Glass Animals",
                    "Stay The Kid LAROI Justin Bieber",
                    "Ghost Justin Bieber",
                    "Industry Baby Lil Nas X",
                    "Good 4 U Olivia Rodrigo",
                    "Levitating Dua Lipa"
                ]

            random_chart_song = random.choice(trending_songs)

            loading_embed = self.make_embed(
                title="Loading chart",
                description=f"Selected: {random_chart_song}\nPreparing...",
                color=0x3498db,
            )
            await loading_message.edit(embed=loading_embed)

        except Exception as e:
            print(f"Fehler beim Abrufen der Charts: {e}")
            fallback_songs = [
                "Flowers Miley Cyrus",
                "As It Was Harry Styles",
                "Bad Habit Steve Lacy",
                "About Damn Time Lizzo",
                "Heat Waves Glass Animals"
            ]
            random_chart_song = random.choice(fallback_songs)

            loading_embed = self.make_embed(
                title="Loading chart (fallback)",
                description=f"Selected: {random_chart_song}\nPreparing...",
                color=0xe67e22,
            )
            await loading_message.edit(embed=loading_embed)

        search_query = f"ytsearch:{random_chart_song}"

        try:
            info = await song_loader.extract_info_async(search_query)
        except Exception as e:
            error_embed = self.make_embed(
                title="Error",
                description=f"Failed to load chart song.\n\n{e}",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        if interaction.guild.id not in guild_queues:
            guild_queues[interaction.guild.id] = OptimizedQueue()

        queue = guild_queues[interaction.guild.id]

        entry = info["entries"][0] if "entries" in info and info["entries"] else info

        processed_song = await self.process_single_entry(entry)
        if processed_song:
            queue.add(processed_song)
            title = processed_song['title']
            thumbnail = processed_song['thumbnail']

            success_embed = self.make_embed(
                title="Added to queue",
                description=title,
                color=0x2ecc71,
                thumbnail=thumbnail,
                fields=[
                    ("Position", f"```\n#{len(queue.queue)}\n```", True)
                ]
            )

            await interaction.channel.send(embed=success_embed)

        try:
            await loading_message.delete()
        except Exception:
            pass

        if not interaction.user.voice:
            await interaction.followup.send(
                embed=self.make_embed(
                    title="Voice channel required",
                    description="Join a voice channel and try again.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            channel = interaction.user.voice.channel
            await channel.connect(self_deaf=True)
            voice_client = interaction.guild.voice_client
            voice_channel = voice_client.channel

            if SET_VC_STATUS_TO_MUSIC_PLAYING:
                current_song = (queue.peek()['title'] if queue.peek() else "Music")
                try:
                    await voice_channel.edit(status=f"Listening to: {current_song}")
                except Exception:
                    pass

        if voice_client and voice_client.channel and interaction.user.voice.channel != voice_client.channel:
            await interaction.followup.send(
                embed=self.make_embed(
                    title="Wrong voice channel",
                    description="You must be in the same voice channel as the bot.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
        else:
            if not queue.playing and not voice_client.is_playing() and not queue.is_empty():
                await self.play_next(guild=interaction.guild, voice_client=voice_client, interaction=interaction)

    async def insipre_me(self, interaction: discord.Interaction):
        if await self.check_timeout_decorator(interaction):
            return
        else:
            await interaction.response.defer()

        random_songs = [
            "Never Gonna Give You Up Rick Astley",
            "Bohemian Rhapsody Queen",
            "Imagine Dragons Believer",
            "The Weeknd Blinding Lights",
            "Dua Lipa Levitating",
            "Ed Sheeran Shape of You",
            "Billie Eilish bad guy",
            "Post Malone Circles",
            "Ariana Grande 7 rings",
            "Drake God's Plan",
            "Taylor Swift Anti-Hero",
            "Harry Styles As It Was",
            "Olivia Rodrigo good 4 u",
            "Doja Cat Kiss Me More",
            "The Kid LAROI Stay",
            "Lil Nas X Industry Baby",
            "Glass Animals Heat Waves",
            "Måneskin Beggin",
            "Adele Easy On Me",
            "Bruno Mars Uptown Funk",
            "Queen Don't Stop Me Now",
            "Journey Don't Stop Believin'",
            "Michael Jackson Billie Jean",
            "A-ha Take On Me",
            "Whitney Houston I Wanna Dance with Somebody (Who Loves Me)",
            "Toto Africa",
            "Eurythmics Sweet Dreams (Are Made of This)",
            "Guns N' Roses Sweet Child O' Mine",
            "AC/DC Back In Black",
            "Nirvana Smells Like Teen Spirit",
            "The Police Every Breath You Take",
            "Linkin Park In The End",
            "The Killers Mr. Brightside",
            "Arctic Monkeys Do I Wanna Know?",
            "Coldplay Viva La Vida",
            "Coldplay Yellow",
            "OneRepublic Counting Stars",
            "Lewis Capaldi Someone You Loved",
            "James Arthur Say You Won't Let Go",
            "Shawn Mendes Señorita",
            "Miley Cyrus Flowers",
            "SZA Kill Bill",
            "Jung Kook Seven",
            "Elton John Cold Heart",
            "The Neighbourhood Sweater Weather",
            "Hozier Take Me to Church",
            "Lord Huron The Night We Met",
            "Vance Joy Riptide",
            "Tones And I Dance Monkey",
            "Post Malone Rockstar",
            "The Chainsmokers Closer",
            "Justin Bieber Sorry",
            "Shawn Mendes Treat You Better",
            "Khalid Better",
            "Cardi B WAP"
        ]

        random_song = random.choice(random_songs)

        loading_embed = self.make_embed(
            title="Loading",
            description=f"Selected: {random_song}\nPreparing...",
            color=0x9b59b6
        )

        loading_message = await interaction.followup.send(embed=loading_embed)

        search_query = f"ytsearch:{random_song}"

        try:
            info = await song_loader.extract_info_async(search_query)
        except Exception as e:
            await interaction.followup.send(
                embed=self.make_embed(
                    title="Error",
                    description=f"Failed to load song.\n\n{e}",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        if interaction.guild.id not in guild_queues:
            guild_queues[interaction.guild.id] = OptimizedQueue()

        queue = guild_queues[interaction.guild.id]

        entry = info["entries"][0] if "entries" in info and info["entries"] else info

        processed_song = await self.process_single_entry(entry)
        if processed_song:
            queue.add(processed_song)
            title = processed_song['title']
            thumbnail = processed_song['thumbnail']

            success_embed = self.make_embed(
                title="Added to queue",
                description=title,
                color=0x9b59b6,
                thumbnail=thumbnail,
                fields=[
                    ("Position", f"```\n#{len(queue.queue)}\n```", True)
                ]
            )

            await interaction.channel.send(embed=success_embed)

        try:
            await loading_message.delete()
        except Exception:
            pass

        if not interaction.user.voice:
            await interaction.followup.send(
                embed=self.make_embed(
                    title="Voice channel required",
                    description="Join a voice channel and try again.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            channel = interaction.user.voice.channel
            await channel.connect(self_deaf=True)
            voice_client = interaction.guild.voice_client
            voice_channel = voice_client.channel

            if SET_VC_STATUS_TO_MUSIC_PLAYING:
                current_song = (queue.peek()['title'] if queue.peek() else "Music")
                try:
                    await voice_channel.edit(status=f"Listening to: {current_song}")
                except Exception:
                    pass

        if voice_client and voice_client.channel and interaction.user.voice.channel != voice_client.channel:
            await interaction.followup.send(
                embed=self.make_embed(
                    title="Wrong voice channel",
                    description="You must be in the same voice channel as the bot.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
        else:
            if not queue.playing and not voice_client.is_playing() and not queue.is_empty():
                await self.play_next(guild=interaction.guild, voice_client=voice_client, interaction=interaction)

    async def mostplayed_callback(self, interaction: discord.Interaction, song: str):
        await interaction.response.defer()

        loading_embed = self.make_embed(
            title="Loading",
            description=f"Selected: {song}\nPreparing...",
            color=0x3498db
        )

        loading_message = await interaction.followup.send(embed=loading_embed)

        search_query = f"ytsearch:{song}"

        try:
            info = await song_loader.extract_info_async(search_query)
        except Exception as e:
            await interaction.followup.send(
                embed=self.make_embed(
                    title="Error",
                    description=f"Failed to load song.\n\n{e}",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        if interaction.guild.id not in guild_queues:
            guild_queues[interaction.guild.id] = OptimizedQueue()

        queue = guild_queues[interaction.guild.id]

        entry = info["entries"][0] if "entries" in info and info["entries"] else info

        processed_song = await self.process_single_entry(entry)
        if processed_song:
            queue.add(processed_song)
            title = processed_song['title']
            thumbnail = processed_song['thumbnail']

            success_embed = self.make_embed(
                title="Added to queue",
                description=title,
                color=0xf39c12,
                thumbnail=thumbnail,
                fields=[
                    ("Position", f"```\n#{len(queue.queue)}\n```", True)
                ]
            )

            await interaction.channel.send(embed=success_embed)

        try:
            await loading_message.delete()
        except Exception:
            pass

        if not interaction.user.voice:
            await interaction.followup.send(
                embed=self.make_embed(
                    title="Voice channel required",
                    description="Join a voice channel and try again.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            channel = interaction.user.voice.channel
            await channel.connect(self_deaf=True)
            voice_client = interaction.guild.voice_client
            voice_channel = voice_client.channel

            if SET_VC_STATUS_TO_MUSIC_PLAYING:
                current_song = (queue.peek()['title'] if queue.peek() else "Music")
                try:
                    await voice_channel.edit(status=f"Listening to: {current_song}")
                except Exception:
                    pass

        if voice_client and voice_client.channel and interaction.user.voice.channel != voice_client.channel:
            await interaction.followup.send(
                embed=self.make_embed(
                    title="Wrong voice channel",
                    description="You must be in the same voice channel as the bot.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
        else:
            if not queue.playing and not voice_client.is_playing() and not queue.is_empty():
                await self.play_next(guild=interaction.guild, voice_client=voice_client, interaction=interaction)

    @app_commands.command(name="play", description="Plays music")
    @app_commands.describe(song="URL or search term")
    async def play(self, interaction: discord.Interaction, song: str):
        if await self.check_timeout_decorator(interaction):
            return
        else:
            try:
                await interaction.response.defer()
            except:
                pass

        if interaction.guild.id not in guild_queues:
            guild_queues[interaction.guild.id] = OptimizedQueue()
        queue = guild_queues[interaction.guild.id]
        voice_client = interaction.guild.voice_client

        if voice_client and voice_client.channel and interaction.user.voice and interaction.user.voice.channel != voice_client.channel:
            await interaction.followup.send(
                embed=self.make_embed(
                    title="Wrong voice channel",
                    description="You must be in the same voice channel as the bot.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        if not interaction.user.voice:
            await interaction.followup.send(
                embed=self.make_embed(
                    title="Voice channel required",
                    description="Join a voice channel and try again.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        loading_embed = self.make_embed(
            title="Loading",
            description=f"Searching for: {song}",
            color=0x3498db
        )
        loading_message = await interaction.followup.send(embed=loading_embed)

        search_query = song if song.startswith("http") else f"ytsearch:{song}"

        try:
            info = await song_loader.extract_info_async(search_query)
        except Exception as e:
            await interaction.followup.send(
                embed=self.make_embed(
                    title="Error",
                    description=f"Failed to load video/playlist.\n\n{e}",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        processing_message = None

        if "entries" in info:
            entries = [e for e in info["entries"] if e]

            processing_embed = self.make_embed(
                title="Processing playlist",
                description=f"Found {len(entries)} items.\nAdding to queue...",
                color=0xf39c12
            )

            processing_message = await interaction.channel.send(embed=processing_embed)

            processed_songs = await self.process_song_entries(entries, interaction.guild.id)

            titles_list = "\n".join([f"- {song['title']}" for song in processed_songs[:10]])
            if len(processed_songs) > 10:
                titles_list += f"\n\n...and {len(processed_songs) - 10} more."

            initial_len = max(0, len(queue.queue) - len(processed_songs))
            wait_seconds = sum(song['duration'] for song in queue.queue[:initial_len]) if initial_len > 0 else 0

            success_embed = self.make_embed(
                title="Playlist added",
                description=f"{len(processed_songs)} songs added to queue.\n\n{titles_list}",
                color=0x2ecc71,
                thumbnail=(entries[0].get("thumbnail") if entries else None),
                fields=[
                    ("Position", f"```\n#{initial_len + 1}\n```", True),
                    ("Estimated time", f"```\n{self.format_time(wait_seconds)}\n```", True),
                ]
            )

            await interaction.channel.send(embed=success_embed)

        else:
            processed_song = await self.process_single_entry(info)
            if processed_song:
                queue.add(processed_song)
                title = processed_song['title']
                thumbnail = processed_song['thumbnail']
                duration = processed_song['duration']

                success_embed = self.make_embed(
                    title="Added to queue",
                    description=title,
                    color=0x2ecc71,
                    thumbnail=thumbnail,
                    fields=[
                        ("Duration", f"```\n{self.format_time(duration)}\n```", True),
                        ("Position", f"```\n#{len(queue.queue)}\n```", True),
                    ]
                )

                await interaction.channel.send(embed=success_embed)

        try:
            if processing_message:
                await processing_message.delete()
        except Exception:
            pass
        try:
            await loading_message.delete()
        except Exception:
            pass

        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            channel = interaction.user.voice.channel
            await channel.connect(self_deaf=True)
            voice_client = interaction.guild.voice_client
            voice_channel = voice_client.channel

            if SET_VC_STATUS_TO_MUSIC_PLAYING:
                current_song = (queue.peek()['title'] if queue.peek() else "Music")
                try:
                    await voice_channel.edit(status=f"Listening to: {current_song}")
                except Exception:
                    pass

        if not queue.playing and not voice_client.is_playing():
            await self.play_next(guild=interaction.guild, voice_client=voice_client, interaction=interaction)

    @app_commands.command(name="skip", description="skips the current song")
    async def skip(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if await self.check_timeout_decorator(interaction):
            return

        if not voice_client or not voice_client.is_playing():
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="Nothing playing",
                    description="Use /play to start music.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        if not interaction.user.voice or interaction.user.voice.channel != voice_client.channel:
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="Wrong voice channel",
                    description="You must be in the same voice channel as the bot.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        queue = guild_queues.get(interaction.guild.id)
        if queue:
            queue.playing = False

        voice_client.stop()

        next_song = queue.queue[0] if queue and queue.queue else None

        if next_song:
            title = next_song['title']
            thumbnail = next_song['thumbnail']

            skip_embed = self.make_embed(
                title="Skipped",
                description=f"Up next: {title}",
                color=0x3498db,
                thumbnail=thumbnail,
                fields=[
                    ("Songs left", f"```\n{len(queue.queue) - 1}\n```", True)
                ]
            )

            await interaction.response.send_message(embed=skip_embed)
        else:
            skip_embed = self.make_embed(
                title="Skipped",
                description="Queue is empty.",
                color=0x95a5a6
            )

            await interaction.response.send_message(embed=skip_embed)

        if queue and not queue.playing:
            await self.play_next(interaction.guild, voice_client, interaction=interaction)

    @app_commands.command(name="queue", description="lists queued songs")
    async def list(self, interaction: discord.Interaction):
        queue = guild_queues.get(interaction.guild.id)
        wait_time = 0
        if await self.check_timeout_decorator(interaction):
            return

        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.channel:
            if not interaction.user.voice or interaction.user.voice.channel != voice_client.channel:
                await interaction.response.send_message(
                    embed=self.make_embed(
                        title="Wrong voice channel",
                        description="You must be in the same voice channel as the bot.",
                        color=0xe74c3c
                    ),
                    ephemeral=True
                )
                return

        if not queue or not queue.queue:
            empty_embed = self.make_embed(
                title="Queue is empty",
                description="Use /play to add some music.",
                color=0x95a5a6,
                fields=[
                    ("Quick start", "```\n/play <song>\n/chart\n```", False)
                ]
            )
            await interaction.response.send_message(embed=empty_embed)
            return

        embed = self.make_embed(
            title=f"Queue ({len(queue.queue)})",
            description="Upcoming tracks:",
            color=0x5865F2,
            author_name=interaction.user.display_name,
            author_icon=safe_avatar(interaction.user),
            footer="Use /skip to skip the current song",
            footer_icon=safe_avatar(self.bot.user),
            thumbnail=safe_avatar(interaction.user)
        )

        display_count = min(15, len(queue.queue))
        for i, song_data in enumerate(queue.queue[:display_count]):
            title = song_data['title']
            duration = song_data['duration']
            embed.add_field(
                name=f"{i + 1}. {title}",
                value=f"```\nDuration: {self.format_time(duration)} • Starts in: {self.format_time(wait_time)}\n```",
                inline=False
            )
            wait_time += duration

        total_duration = self.format_time(sum(song['duration'] for song in queue.queue))
        if len(queue.queue) > display_count:
            embed.add_field(
                name="More",
                value=f"```\n+{len(queue.queue) - display_count} more\nTotal duration: {total_duration}\n```",
                inline=False
            )
        else:
            embed.add_field(
                name="Summary",
                value=f"```\nTotal duration: {total_duration}\n```",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stop", description="Disconnects the Bot")
    async def leave(self, i: discord.Interaction):
        if await self.check_timeout_decorator(i):
            return
        voice_client = i.guild.voice_client
        if voice_client and voice_client.channel:
            if not i.user.voice or i.user.voice.channel != voice_client.channel:
                await i.response.send_message(
                    embed=self.make_embed(
                        title="Wrong voice channel",
                        description="You must be in the same voice channel as the bot.",
                        color=0xe74c3c
                    ),
                    ephemeral=True
                )
                return

        queue = guild_queues.get(i.guild.id)

        if queue and queue.queue:
            total_duration = sum(song_data[3] for _source, song_data in queue.queue)
            cleared_count = len(queue.queue)
            queue.clear()
        else:
            total_duration = 0
            cleared_count = 0

        embed = self.make_embed(
            title="Disconnected",
            description="Left the voice channel.",
            color=0xe74c3c,
            author_name=i.user.display_name,
            author_icon=safe_avatar(i.user),
            footer="See you next time!",
            footer_icon=safe_avatar(self.bot.user),
            thumbnail=safe_avatar(i.user),
            fields=[
                ("Session summary",
                 f"```\nTime left in queue: {self.format_time(total_duration)}\nSongs cleared: {cleared_count}\n```",
                 False)
            ]
        )

        if i.guild.voice_client:
            voice_channel = voice_client.channel
            try:
                await voice_channel.edit(status=None)
            except Exception:
                pass
            await i.guild.voice_client.disconnect()
            await i.response.send_message(embed=embed)
            await self.send_static_message()
        else:
            await i.response.send_message(
                embed=self.make_embed(
                    title="Not connected",
                    description="The bot is not connected to a voice channel.",
                    color=0xe74c3c
                )
            )

    @app_commands.command(name="shuffle", description="Shuffles the queue")
    async def shuffle(self, interaction: discord.Interaction):
        if await self.check_timeout_decorator(interaction):
            return

        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.channel:
            if not interaction.user.voice or interaction.user.voice.channel != voice_client.channel:
                await interaction.response.send_message(
                    embed=self.make_embed(
                        title="Wrong voice channel",
                        description="You must be in the same voice channel as the bot.",
                        color=0xe74c3c
                    ),
                    ephemeral=True
                )
                return

        queue = guild_queues.get(interaction.guild.id)

        if not queue or not queue.queue:
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="Queue is empty",
                    description="Nothing to shuffle.",
                    color=0x95a5a6
                ),
                ephemeral=True
            )
            return

        random.shuffle(queue.queue)

        embed = self.make_embed(
            title="Queue shuffled",
            description=f"{len(queue.queue)} songs reshuffled.",
            color=0x5865F2,
            author_name=interaction.user.display_name,
            author_icon=safe_avatar(interaction.user),
            footer="Enjoy!",
            footer_icon=safe_avatar(self.bot.user),
            thumbnail=safe_avatar(interaction.user)
        )

        wait_time = 0
        display_count = min(10, len(queue.queue))
        for i, (source, song_data) in enumerate(queue.queue[:display_count]):
            title = song_data[0]
            duration = song_data[3]

            embed.add_field(
                name=f"{i + 1}. {title}",
                value=f"```\nDuration: {self.format_time(duration)} • Starts in: {self.format_time(wait_time)}\n```",
                inline=False
            )
            wait_time += duration

        total_duration = self.format_time(sum(song['duration'] for song in queue.queue))
        if len(queue.queue) > display_count:
            embed.add_field(
                name="More",
                value=f"```\n+{len(queue.queue) - display_count} more\nTotal duration: {total_duration}\n```",
                inline=False
            )
        else:
            embed.add_field(
                name="Summary",
                value=f"```\nTotal duration: {total_duration}\n```",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pause", description="Pauses or resumes the playback")
    async def pause(self, interaction: discord.Interaction):
        if await self.check_timeout_decorator(interaction):
            return
        voice_client = interaction.guild.voice_client

        if not voice_client or (not voice_client.is_playing() and not voice_client.is_paused()):
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="Nothing playing",
                    description="Use /play to start music.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        if not interaction.user.voice or interaction.user.voice.channel != voice_client.channel:
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="Wrong voice channel",
                    description="You must be in the same voice channel as the bot.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        if voice_client.is_paused():
            voice_client.resume()
            embed = self.make_embed(
                title="Resumed",
                description="Playback resumed.",
                color=0x2ecc71,
                author_name=interaction.user.display_name,
                author_icon=safe_avatar(interaction.user),
                footer="Use /pause to toggle",
                footer_icon=safe_avatar(self.bot.user)
            )
        else:
            voice_client.pause()
            embed = self.make_embed(
                title="Paused",
                description="Playback paused.",
                color=0xf39c12,
                author_name=interaction.user.display_name,
                author_icon=safe_avatar(interaction.user),
                footer="Use /pause to toggle",
                footer_icon=safe_avatar(self.bot.user)
            )

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        if before.channel and before.channel != after.channel:
            voice_client = before.channel.guild.voice_client
            if voice_client and voice_client.channel == before.channel:
                members_in_channel = [m for m in before.channel.members if not m.bot]
                if len(members_in_channel) == 0:
                    await asyncio.sleep(5)

                    if voice_client.is_connected():
                        current_members = [m for m in voice_client.channel.members if not m.bot]
                        if len(current_members) == 0:
                            guild_id = before.channel.guild.id
                            queue = guild_queues.get(guild_id)
                            if queue:
                                queue.clear()
                                queue.playing = False
                                del guild_queues[guild_id]
                            voice_channel = voice_client.channel
                            try:
                                await voice_channel.edit(status=None)
                            except Exception:
                                pass
                            await voice_client.disconnect(force=True)
                            try:
                                channel = await self.bot.fetch_channel(I_CHANNEL)
                                if channel:
                                    await self.send_static_message()
                                else:
                                    print(f"Error: Channel with ID {I_CHANNEL} not found after fetch.")
                            except Exception as e:
                                print(f"Error sending auto-disconnect message: {e}")

    @commands.Cog.listener("on_voice_state_update")
    async def on_voice_state_update_bot_kick(self, member, before, after):
        if member.id == self.bot.user.id and before.channel is not None and after.channel is None:
            guild_id = before.channel.guild.id
            if guild_id in guild_queues:
                queue = guild_queues[guild_id]
                queue.clear()
                queue.playing = False
                del guild_queues[guild_id]
            try:
                channel = await self.bot.fetch_channel(I_CHANNEL)
                if channel:
                    await self.send_static_message()
            except Exception as e:
                print(f"Error sending disconnect message: {e}")

    @app_commands.command(name="musicmute", description="Timeout a user from using music commands")
    @app_commands.describe(user="The user to timeout", duration="Duration in minutes")
    async def timeout_user_command(self, interaction: discord.Interaction, user: discord.Member, duration: int):
        await self.timeout_user(interaction, user, duration)

    async def timeout_user(self, interaction: discord.Interaction, user: discord.Member, duration: int):
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="No permission",
                    description="You don't have permission to timeout users.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        if duration <= 0 or duration > 10000:
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="Invalid duration",
                    description="Duration must be between 1 and 10000 minutes.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        timeout_file = "timeouts.json"
        timeouts = {}

        if os.path.exists(timeout_file):
            try:
                with open(timeout_file, 'r') as f:
                    timeouts = json.load(f)
            except json.JSONDecodeError:
                timeouts = {}

        end_time = datetime.now() + timedelta(minutes=duration)

        timeouts[str(user.id)] = {
            "user_id": user.id,
            "username": user.display_name,
            "timeout_by": interaction.user.id,
            "timeout_by_name": interaction.user.display_name,
            "start_time": datetime.now().isoformat(),
            "end_time": end_time.isoformat(),
            "duration_minutes": duration,
            "guild_id": interaction.guild.id
        }

        try:
            with open(timeout_file, 'w') as f:
                json.dump(timeouts, f, indent=2)
        except Exception as e:
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="Error",
                    description=f"Failed to save timeout data.\n\n{e}",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        embed = self.make_embed(
            title="User timed out",
            description=f"{user.display_name} has been muted from music commands.",
            color=0xe67e22,
            thumbnail=safe_avatar(user),
            fields=[
                ("Duration", f"```\n{duration} minutes\n```", True),
                ("Ends at", f"```\n{end_time.strftime('%H:%M:%S')}\n```", True),
                ("Moderator", f"```\n{interaction.user.display_name}\n```", True),
            ]
        )

        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10, silent=True)

    def cleanup_expired_timeouts(self):
        timeout_file = "timeouts.json"

        if not os.path.exists(timeout_file):
            return

        try:
            with open(timeout_file, 'r') as f:
                timeouts = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return

        current_time = datetime.now()
        expired_users = []

        for user_id, timeout_data in list(timeouts.items()):
            end_time = datetime.fromisoformat(timeout_data["end_time"])
            if current_time > end_time:
                expired_users.append(user_id)

        for user_id in expired_users:
            del timeouts[user_id]

        if expired_users:
            try:
                with open(timeout_file, 'w') as f:
                    json.dump(timeouts, f, indent=2)
            except Exception as e:
                print(f"Error updating timeout file: {e}")

    def is_user_timed_out(self, user_id: int) -> bool:
        self.cleanup_expired_timeouts()

        timeout_file = "timeouts.json"

        if not os.path.exists(timeout_file):
            return False

        try:
            with open(timeout_file, 'r') as f:
                timeouts = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return False

        user_key = str(user_id)
        if user_key not in timeouts:
            return False

        end_time = datetime.fromisoformat(timeouts[user_key]["end_time"])
        if datetime.now() > end_time:
            del timeouts[user_key]
            try:
                with open(timeout_file, 'w') as f:
                    json.dump(timeouts, f, indent=2)
            except Exception:
                pass
            return False

        return True

    async def check_timeout_decorator(self, interaction: discord.Interaction):
        if self.is_user_timed_out(interaction.user.id):
            timeout_file = "timeouts.json"
            with open(timeout_file, 'r') as f:
                timeouts = json.load(f)

            user_timeout = timeouts[str(interaction.user.id)]
            end_time = datetime.fromisoformat(user_timeout["end_time"])
            remaining_minutes = max(0, int((end_time - datetime.now()).total_seconds() / 60))

            embed = self.make_embed(
                title="Muted",
                description="You cannot use music commands right now.",
                color=0xe74c3c,
                fields=[
                    ("Time remaining", f"```\n{remaining_minutes} minutes\n```", True),
                    ("Ends at", f"```\n{end_time.strftime('%H:%M:%S')}\n```", True),
                    ("By", f"```\n{user_timeout['timeout_by_name']}\n```", True),
                ]
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return True
        return False

    @app_commands.command(name="unmusicmute", description="Remove timeout from a user")
    @app_commands.describe(user="The user to remove timeout from")
    async def untimeout_user(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="No permission",
                    description="You don't have permission to remove timeouts.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        timeout_file = "timeouts.json"

        if not os.path.exists(timeout_file):
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="No timeouts",
                    description="No timeout data found.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        try:
            with open(timeout_file, 'r') as f:
                timeouts = json.load(f)
        except json.JSONDecodeError:
            timeouts = {}

        user_key = str(user.id)
        if user_key not in timeouts:
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="Not muted",
                    description=f"{user.display_name} is not currently muted.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        del timeouts[user_key]

        try:
            with open(timeout_file, 'w') as f:
                json.dump(timeouts, f, indent=2)
        except Exception as e:
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="Error",
                    description=f"Failed to save timeout data.\n\n{e}",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        embed = self.make_embed(
            title="Timeout removed",
            description=f"{user.display_name} can now use music commands again.",
            color=0x2ecc71,
            thumbnail=safe_avatar(user),
            fields=[
                ("Removed by", f"```\n{interaction.user.display_name}\n```", True)
            ]
        )

        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="clearqueue", description="Vote to clear the entire queue")
    async def clear_queue(self, interaction: discord.Interaction):
        if await self.check_timeout_decorator(interaction):
            return

        voice_client = interaction.guild.voice_client

        if not interaction.user.voice:
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="Voice channel required",
                    description="Join a voice channel and try again.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        if interaction.user.voice.channel != voice_client.channel:
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="Wrong voice channel",
                    description="You must be in the same voice channel as the bot to start a vote.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        queue = guild_queues.get(guild_id)

        if interaction.user.guild_permissions.kick_members:
            cleared_count = len(queue.queue)
            total_duration = sum(song['duration'] for song in queue.queue)
            queue.clear()
            queue.playing = False
            try:
                voice_client.stop()
            except Exception:
                pass

            embed = self.make_embed(
                title="Queue cleared",
                description=f"Cleared by {interaction.user.display_name}.",
                color=0x2ecc71,
                thumbnail=safe_avatar(interaction.user),
                fields=[
                    ("Songs cleared", f"```\n{cleared_count}\n```", True),
                    ("Time removed", f"```\n{self.format_time(total_duration)}\n```", True)
                ]
            )
            await interaction.response.send_message(embed=embed)
            return

        voters = [m for m in voice_client.channel.members if not m.bot]
        total_voters = len(voters)
        if total_voters == 0:
            await interaction.response.send_message(
                embed=self.make_embed(
                    title="No voters",
                    description="No eligible voters in the voice channel.",
                    color=0xe74c3c
                ),
                ephemeral=True
            )
            return

        if total_voters == 1:
            cleared_count = len(queue.queue)
            total_duration = sum(song['duration'] for song in queue.queue)
            queue.clear()
            queue.playing = False
            try:
                voice_client.stop()
            except Exception:
                pass
            embed = self.make_embed(
                title="Queue cleared",
                description=f"Cleared by {interaction.user.display_name}.",
                color=0x2ecc71,
                thumbnail=safe_avatar(interaction.user),
                fields=[
                    ("Songs cleared", f"```\n{cleared_count}\n```", True),
                    ("Time removed", f"```\n{self.format_time(total_duration)}\n```", True)
                ]
            )
            await interaction.response.send_message(embed=embed)
            return

        required = (total_voters // 2) + 1
        vote_duration = 20

        parent = self

        class VoteView(discord.ui.View):
            def __init__(self, voters_ids, required_count, timeout_seconds):
                super().__init__(timeout=timeout_seconds)
                self.voters = set(voters_ids)
                self.yes = set()
                self.no = set()
                self.required = required_count
                self.ended_early = False
                self.result_embed = None

            async def update_message_embed(self, message: discord.Message):
                try:
                    embed = message.embeds[0]
                    embed.description = (
                        f"{interaction.user.display_name} started a vote to clear the queue.\n\n"
                        f"Members in voice channel: {total_voters}\n"
                        f"Required votes to clear: {self.required}\n\n"
                        f"✅ Yes: {len(self.yes)} • ❌ No: {len(self.no)}\n\n"
                        f"Voting ends in {vote_duration} seconds."
                    )
                    await message.edit(embed=embed, view=self)
                except Exception:
                    pass

            @discord.ui.button(label="✅ Yes", style=discord.ButtonStyle.success)
            async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                uid = interaction.user.id
                if uid not in self.voters:
                    await interaction.response.send_message("You are not eligible to vote in this vote.", ephemeral=True)
                    return
                if uid in self.yes:
                    self.yes.remove(uid)
                    await interaction.response.send_message("Removed your ✅ vote.", ephemeral=True)
                else:
                    self.yes.add(uid)
                    self.no.discard(uid)
                    await interaction.response.send_message("Registered your ✅ vote.", ephemeral=True)
                await self.update_message_embed(interaction.message)

                if len(self.yes) >= self.required and not self.ended_early:
                    cleared_count = len(queue.queue)
                    total_duration = sum(song['duration'] for song in queue.queue)
                    queue.clear()
                    queue.playing = False
                    try:
                        voice_client.stop()
                    except Exception:
                        pass

                    result_embed = parent.make_embed(
                        title="Vote passed",
                        description=f"Queue cleared ({len(self.yes)}/{total_voters} voted yes).",
                        color=0x2ecc71,
                        fields=[
                            ("Songs cleared", f"```\n{cleared_count}\n```", True),
                            ("Time removed", f"```\n{parent.format_time(total_duration)}\n```", True)
                        ]
                    )

                    self.ended_early = True
                    self.result_embed = result_embed

                    for child in self.children:
                        child.disabled = True
                    try:
                        await interaction.message.edit(embed=result_embed, view=self)
                    except Exception:
                        pass

                    try:
                        await interaction.followup.send(embed=result_embed)
                    except Exception:
                        pass

                    self.stop()

            @discord.ui.button(label="❌ No", style=discord.ButtonStyle.danger)
            async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                uid = interaction.user.id
                if uid not in self.voters:
                    await interaction.response.send_message("You are not eligible to vote in this vote.", ephemeral=True)
                    return
                if uid in self.no:
                    self.no.remove(uid)
                    await interaction.response.send_message("Removed your ❌ vote.", ephemeral=True)
                else:
                    self.no.add(uid)
                    self.yes.discard(uid)
                    await interaction.response.send_message("Registered your ❌ vote.", ephemeral=True)
                await self.update_message_embed(interaction.message)

        vote_embed = self.make_embed(
            title="Vote to clear queue",
            description=(
                f"{interaction.user.display_name} started a vote to clear the queue.\n\n"
                f"Members in voice channel: {total_voters}\n"
                f"Required votes to clear: {required}\n\n"
                f"React by clicking a button. Voting ends in {vote_duration} seconds."
            ),
            color=0xf1c40f,
            thumbnail=safe_avatar(interaction.user)
        )

        view = VoteView([m.id for m in voters], required, vote_duration)

        await interaction.response.send_message(embed=vote_embed, view=view)
        vote_message = await interaction.original_response()

        await view.wait()

        if getattr(view, "ended_early", False):
            return

        for child in view.children:
            child.disabled = True
        try:
            await vote_message.edit(view=view)
        except Exception:
            pass

        yes_count = len(view.yes)
        no_count = len(view.no)

        yes_count = min(yes_count, total_voters)
        no_count = min(no_count, total_voters)

        if yes_count >= required:
            cleared_count = len(queue.queue)
            total_duration = sum(song['duration'] for song in queue.queue)
            queue.clear()
            queue.playing = False
            try:
                voice_client.stop()
            except Exception:
                pass

            result_embed = self.make_embed(
                title="Vote passed",
                description=f"Queue cleared ({yes_count}/{total_voters} voted yes).",
                color=0x2ecc71,
                fields=[
                    ("Songs cleared", f"```\n{cleared_count}\n```", True),
                    ("Time removed", f"```\n{self.format_time(total_duration)}\n```", True)
                ]
            )
        else:
            result_embed = self.make_embed(
                title="Vote failed",
                description=f"Not enough votes to clear the queue ({yes_count}/{total_voters} voted yes).",
                color=0x95a5a6,
                fields=[
                    ("Yes", f"```\n{yes_count}\n```", True),
                    ("No", f"```\n{no_count}\n```", True),
                    ("Required", f"```\n{required}\n```", True)
                ]
            )

        try:
            await vote_message.reply(embed=result_embed)
        except Exception:
            await interaction.followup.send(embed=result_embed)

    async def cog_load(self):
        self.bot.tree.add_command(self.play, guild=discord.Object(id=SYNC_SERVER))
        self.bot.tree.add_command(self.skip, guild=discord.Object(id=SYNC_SERVER))
        self.bot.tree.add_command(self.list, guild=discord.Object(id=SYNC_SERVER))
        self.bot.tree.add_command(self.leave, guild=discord.Object(id=SYNC_SERVER))
        self.bot.tree.add_command(self.shuffle, guild=discord.Object(id=SYNC_SERVER))
        self.bot.tree.add_command(self.play_chart, guild=discord.Object(id=SYNC_SERVER))
        self.bot.tree.add_command(self.pause, guild=discord.Object(id=SYNC_SERVER))
        self.bot.tree.add_command(self.timeout_user_command, guild=discord.Object(id=SYNC_SERVER))
        self.bot.tree.add_command(self.clear_queue, guild=discord.Object(id=SYNC_SERVER))

    async def cog_unload(self):
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
        song_loader.executor.shutdown(wait=False)
