import discord
from discord.ext import commands
import os
import datetime
from datetime import timedelta
from typing import Literal
import aiohttp

api_url = os.getenv("API_URL")
apiPasskey = os.getenv("API_PASSKEY")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=".", intents=intents)

async def getGroupName(number):
    payload = {
        "passkey": apiPasskey,
        "number": number,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{api_url}/stats/name", json=payload) as response:
            data = await response.json()
            if data:
                return data['name']
            else:
                return "N/A"

async def checkUserHours(user_id, time_frame, number = None):
    payload = {
        "passkey": apiPasskey,
        "userId": user_id,
        "timeFrame": time_frame,
        "number": number,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{api_url}/stats/user", json=payload) as response:
            data = await response.json()
            if data:
                return data
            else:
                return None

class HoursCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    hours_group = discord.app_commands.Group(name="hours", description="Hours management commands")

    @hours_group.command(name="user", description="Provides hour information about a particular user")
    @discord.app_commands.describe(time_frame = "Time frame to get hour information about", user = "User to get hour information on", group = "[OPTIONAL] Get hour information on a particular group", hidden = "[OPTIONAL] Whether to make the response hidden or not")
    async def userinfo(self, interaction: discord.Interaction, time_frame: Literal["This Week", "Last Week", "This Month", "Last Month", "All Time"], user: discord.User = None, group: str = None, hidden: bool = None):
        if hidden is None:
            hidden = False
        if user is None:
            user = interaction.user
        await interaction.response.defer(ephemeral=hidden)
        data = await checkUserHours(user.id, time_frame, group)
        if data and data['rows']:
            group_list = "N/A"
            hour_list = "N/A"
            for row in data['rows']:
                group_list += f"{getGroupName(row[0])}\n"
                hour_list += f"{row[1]/3600:.2f}\n"
            embed = discord.Embed(title="User Hour Information", color=discord.Color.blurple())
            embed.add_field(name="Group", value=group_list, inline=True)
            embed.add_field(name="Hours", value=hour_list, inline=True)
        else:
            embed = discord.Embed(title="User Hour Information", description=f"{user.mention} has no clocked hours in this time period!", color=discord.Color.red())
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HoursCog(bot))