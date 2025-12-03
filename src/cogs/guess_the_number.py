# ruff: noqa: F403 F405
from discord.ext import commands
from util.constants import *
from discord import *
from discord.ui import View, Button
import random
import asyncio
from datetime import datetime, timedelta

class GuessNumberCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_number = None
        self.difficulty = None
        self.numb_of_guesses = 0
        self.awaiting_custom_input = False
        self.user_timeouts = {}
        self.timeout_duration = 2
        
    async def game_start(self, difficulty: str, custom_value: int = None):
        difficulty_ranges = {
            "easy": (1, 100),
            "normal": (1, 1000),
            "hard": (1, 10000)
        }
        
        if difficulty in difficulty_ranges:
            min_val, max_val = difficulty_ranges[difficulty]
            self.bot_number = random.randint(min_val, max_val)
            self.difficulty = difficulty.capitalize()
        elif difficulty == "custom" and custom_value:
            self.bot_number = random.randint(1, custom_value)
            self.difficulty = f"Custom range of 1 - {custom_value}"
        
        self.numb_of_guesses = 0
        print(f"Game started - Number: {self.bot_number}")

    def is_user_on_cooldown(self, user_id: int) -> bool:
        if user_id in self.user_timeouts:
            time_left = self.user_timeouts[user_id] - datetime.now()
            return time_left.total_seconds() > 0
        return False

    def get_cooldown_time(self, user_id: int) -> int:
        if user_id in self.user_timeouts:
            time_left = self.user_timeouts[user_id] - datetime.now()
            return max(0, int(time_left.total_seconds()))
        return 0

    def set_user_cooldown(self, user_id: int):
        self.user_timeouts[user_id] = datetime.now() + timedelta(seconds=self.timeout_duration)

    def get_temperature_emoji(self, diff: int) -> str:
        if diff == 0:
            return "🎉"
        elif diff == 1:
            return "🔥"
        elif diff <= 3:
            return "🌋"
        elif diff <= 10:
            return "🌡️"
        elif diff <= 30:
            return "❄️"
        elif diff <= 100:
            return "🧊"
        elif diff <= 500:
            return "🥶"
        else:
            return "💀"

    async def check_number(self, number: int, channel, message: discord.Message):
        if self.bot_number is None:
            if self.awaiting_custom_input:
                await message.delete(delay=2)
                return
            await message.delete(delay=2)
            await channel.send("Game not started yet. Type 'start' to begin.", delete_after=4)
            return

        if self.is_user_on_cooldown(message.author.id):
            cooldown_time = self.get_cooldown_time(message.author.id)
            await message.delete(delay=2)
            await channel.send(
                f"{message.author.mention} Please wait {cooldown_time}s before guessing again!", 
                delete_after=3
            )
            return

        self.set_user_cooldown(message.author.id)

        if number == self.bot_number:
            await channel.send(
                f"{message.author.mention} Congratulations! You guessed the number **{self.bot_number}** "
                f"in **{self.numb_of_guesses + 1}** guesses! 🎉"
            )
            await self.clear_game()
        else:
            self.numb_of_guesses += 1
            diff = abs(number - self.bot_number)
            
            if number < self.bot_number:
                await message.add_reaction("⬆️")
            else:
                await message.add_reaction("⬇️")
            
            temp_emoji = self.get_temperature_emoji(diff)
            await message.add_reaction(temp_emoji)
                
    async def clear_game(self):
        self.bot_number = None
        self.difficulty = None
        self.numb_of_guesses = 0
        self.user_timeouts.clear()

    async def create_difficulty_view(self, message_author) -> View:
        view = View(timeout=60)

        async def easy_callback(interaction):
            await interaction.response.send_message(f"Started on `Easy` difficulty! Good Luck! {CHECK}")
            await self.game_start("easy")

        async def normal_callback(interaction):
            await interaction.response.send_message(f"Started on `Normal` difficulty! Good Luck! {CHECK}")
            await self.game_start("normal")

        async def hard_callback(interaction):
            await interaction.response.send_message(f"Started on `Hard` difficulty! Good Luck, you will need it! {CHECK}")
            await self.game_start("hard")

        async def custom_callback(interaction: discord.Interaction):
            self.awaiting_custom_input = True
            await interaction.response.send_message("Please enter your custom max number:", ephemeral=True)
            
            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel
            
            try:
                custom_msg = await self.bot.wait_for('message', check=check, timeout=30)
                
                if custom_msg.content.strip().lower() in [":q", "quit"]:
                    await custom_msg.delete(delay=2)
                    await interaction.followup.send("Custom difficulty cancelled.", ephemeral=True, delete_after=5)
                    return
                
                custom_input = int(custom_msg.content.strip())
                
                if custom_input < 1:
                    await interaction.followup.send("Please enter a number greater than 0.", ephemeral=True, delete_after=10)
                    return
                
                await custom_msg.delete(delay=2)
                await interaction.followup.send(f"Started on `Custom` difficulty! Range: 1 - {custom_input}! {CHECK}")
                await self.game_start("custom", custom_input)
                
            except ValueError:
                await interaction.followup.send('Please enter a valid number. Or quit with "quit" / ":q".', ephemeral=True, delete_after=10)
            except asyncio.TimeoutError:
                await interaction.followup.send("Timed out. Please try again.", ephemeral=True, delete_after=10)
            finally:
                self.awaiting_custom_input = False

        easy_btn = Button(label="Easy", style=GREEN, emoji="👽")
        easy_btn.callback = easy_callback

        normal_btn = Button(label="Normal", style=SECONDARY, emoji="😀")
        normal_btn.callback = normal_callback

        hard_btn = Button(label="Hard", style=DANGER, emoji="💀")
        hard_btn.callback = hard_callback
        
        custom_btn = Button(label="Custom", style=discord.ButtonStyle.blurple, emoji="❓")
        custom_btn.callback = custom_callback

        view.add_item(easy_btn)
        view.add_item(normal_btn)
        view.add_item(hard_btn)
        view.add_item(custom_btn)
        
        return view

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.channel.name != "guess-number":
            return

        channel = message.channel
        content = message.content.strip().lower()

        try:
            number = int(message.content.strip())
            await self.check_number(number, channel, message)
        except ValueError:
            if content in ["start", ":s"]:
                await self.clear_game()
                await message.delete()
                await channel.send(f"Starting {LOADING_EMOJI}")

                view = await self.create_difficulty_view(message.author)
                
                await channel.last_message.delete()
                await channel.send(f"{message.author.mention} Please select a difficulty:", view=view)
                
            elif content == "difficulty":
                difficulty_text = self.difficulty or "No game active"
                await channel.send(f"{message.author.mention} Current difficulty: `{difficulty_text}`", delete_after=3)
                await message.delete(delay=2)
                
            elif content == "surrender":
                if self.difficulty:
                    await channel.send(
                        f"{message.author.mention} You surrendered! With `{self.numb_of_guesses}` guesses "
                        f"in `{self.difficulty}` difficulty. The number was: `{self.bot_number}`!"
                    )
                    await self.clear_game()
                else:
                    await channel.send("Game not started yet. Type 'start' to begin.", delete_after=4)
                await message.delete(delay=2)
                
            else:
                await message.delete(delay=2)
                await channel.send(f"{message.author.mention} Please only use numbers to guess.", delete_after=3)