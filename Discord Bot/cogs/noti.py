import discord
from discord.ext import commands, tasks
import asyncio
import os
import datetime
from datetime import timedelta
import sqlite3
from typing import Literal
from calendar import monthrange
import aiohttp
from dotenv import load_dotenv
import os

load_dotenv()

api_url = os.getenv("API_URL")
apiPasskey = os.getenv("API_PASSKEY")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=".", intents=intents)

def format_discord_timestamp(datetime_str):
    try:
        dt_object = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S.%f")
        unix_timestamp = int(dt_object.timestamp())
        return f"<t:{unix_timestamp}:R>"
    except ValueError as e:
        return f"Invalid datetime string: {e}"

async def notiApi():
    payload = {
        'passkey': apiPasskey
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{api_url}/time/notifications", json=payload) as response:
            data = await response.json()
            if data and data['notis'] != None:
                return data['notis']
            else:
                return None

class NotiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.noti_loop.start()

    async def cog_unload(self):
        self.noti_loop.cancel()

    @tasks.loop(seconds=10)
    async def noti_loop(self):
        await self.bot.wait_until_ready()
        notis = await notiApi()
        if notis:
            for noti in notis:
                user = await self.bot.fetch_user(noti[1])
                embed = discord.Embed(title="Hour Report", color=discord.Color.blurple())
                embed.add_field(name="Start Time", value=format_discord_timestamp(noti[2]), inline=True)
                embed.add_field(name="End Time", value=format_discord_timestamp(noti[3]), inline=True)
                embed.timestamp = datetime.datetime.now()
                embed.set_footer(text="Atlas Time Tracker")
                try:
                    await user.send(embed=embed)
                except Exception as e:
                    print(e)
                    continue

async def setup(bot):
    await bot.add_cog(NotiCog(bot))