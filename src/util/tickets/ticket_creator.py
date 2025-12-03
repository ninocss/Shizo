# ruff: noqa: F403 F405
import discord
from util.constants import *
from views.ticketviews import *
from modals.ticketmodals import *
import os
import json
from typing import Optional, List

def load_ticket_creator_data() -> dict:
    if not os.path.exists(TICKET_CREATOR_FILE):
        return {}
    try:
        with open(TICKET_CREATOR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return {}

def save_ticket_creator_data(data: dict) -> None:
    try:
        with open(TICKET_CREATOR_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except (IOError, OSError):
        pass

def get_ticket_creator(guild_id: int) -> Optional[int]:
    data = load_ticket_creator_data()
    creator_id = data.get(str(guild_id))
    return int(creator_id) if creator_id is not None else None

def save_ticket_creator(thread_id: int, user_id: int) -> None:
    data = load_ticket_creator_data()
    data[str(thread_id)] = user_id
    save_ticket_creator_data(data)

def delete_ticket_creator(thread_id: int) -> None:
    data = load_ticket_creator_data()
    data.pop(str(thread_id), None)
    save_ticket_creator_data(data)

async def get_ticket_users(thread: discord.Thread) -> List[discord.User]:
    seen_users = {} 
    
    async for message in thread.history(limit=None):
        if message.author.id not in seen_users:
            seen_users[message.author.id] = message.author
    
    return list(seen_users.values())