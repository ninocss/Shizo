# ruff: noqa: F403 F405
from discord.ext import commands
from util.constants import *
from discord import *
import random
import time

async def random_fail_message():
    messages = [
        "I never had mathematics in school, so we have to start over at `1` :(",
        "I messed up! That's not the right number. Let's try again from `1`.",
        "Math is hard for me, isn't it? Back to `1` I go!",
        "I got the wrong number! Resetting the count to `1`.",
        "Looks like I need to start over at `1`. Better luck next time!",
        "That wasn't the expected number from me. Let's begin again at `1`.",
        "Counting is tricky for me! Let's reset to `1`.",
        "Uh oh, that's not it. Back to `1` I go!",
        "Whoops! The count starts from `1` again for me.",
        "Not quite! I'll try counting from `1` once more."
    ]
    return random.choice(messages)

class CountingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.counting_channels = {}
        self.last_user = {}
        self.user_cooldowns = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        if message.channel.name != "counting":
            return
        
        cooldown_key = (message.channel.id, message.author.id)
        current_time = time.time()
        
        if cooldown_key in self.user_cooldowns:
            if current_time - self.user_cooldowns[cooldown_key] < 3:
                await message.delete()
                return
        
        try:
            number = int(eval(message.content.strip()))
        except:
            await message.delete()
            return
        
        self.user_cooldowns[cooldown_key] = current_time
        
        user = message.author
        user_name = user.name
        user_avatar = user.avatar

        channel_id = message.channel.id
        channel = message.channel
        webhook = await channel.create_webhook(name=user_name)
        

        if channel_id not in self.counting_channels:
            self.counting_channels[channel_id] = 0
            self.last_user[channel_id] = None
            
        expected_number = self.counting_channels[channel_id] + 1

        if self.last_user[channel_id] == message.author.id:
            await message.delete(delay=0)
            await webhook.delete()
            return

        if number == expected_number:
            self.counting_channels[channel_id] += 1
            self.last_user[channel_id] = message.author.id
        
            await message.delete(delay=0)
            message = await webhook.send(
                username=user_name,
                avatar_url=user_avatar,
                content=number,
                wait=True
            )
            await message.add_reaction("🎉")

        else:
            await webhook.send(
                username=user_name,
                avatar_url=user_avatar,
                content=await random_fail_message()
            )
            self.counting_channels[channel_id] = 0
            
        await webhook.delete()