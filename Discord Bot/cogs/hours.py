import discord
from discord.ext import commands
import asyncio
import os
import datetime
from datetime import timedelta
import sqlite3
from typing import Literal
from calendar import monthrange

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=".", intents=intents)

conn = sqlite3.connect('time.db')
c = conn.cursor()

class HoursCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="userinfo", description="Provides hour information about a particular user")
    async def userinfo(self, interaction: discord.Interaction, time_frame: Literal["This Week", "Last Week", "This Month", "Last Month", "All Time"], user: discord.User = None, hidden: bool = None):
        if hidden is None:
            hidden = False
        if user is None:
            user = interaction.user
        await interaction.response.defer(ephemeral=hidden)
        today = datetime.datetime.today()
        days_to_subtract = today.weekday() + 1
        last_sunday = today - timedelta(days=days_to_subtract)
        current_sunday = last_sunday
        if time_frame != "All Time":
            if time_frame == "This Month":
                start = today.replace(day=1, hour=0, minute=0, second=0).strftime('%Y-%m-%d %H:%M:%S')
                end = today.strftime('%Y-%m-%d %H:%M:%S')
            elif time_frame == "Last Month":
                first_day_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
                last_day_last_month = first_day_last_month.replace(day=monthrange(first_day_last_month.year, first_day_last_month.month)[1])
                start = first_day_last_month.strftime('%Y-%m-%d %H:%M:%S')
                end = last_day_last_month.strftime('%Y-%m-%d %H:%M:%S')
            elif time_frame == "This Week":
                start = current_sunday.strftime('%Y-%m-%d %H:%M:%S')
                end = today.strftime('%Y-%m-%d %H:%M:%S')
            elif time_frame == "Last Week":
                start = (current_sunday - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
                end = (current_sunday - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
            c.execute("SELECT type, SUM(seconds) as total_hours FROM logs WHERE clockout BETWEEN ? AND ? AND user_id = ? ORDER BY total_hours DESC", (start, end, user.id,))
            rows = c.fetchall()
        else:
            c.execute("SELECT type, SUM(seconds) as total_hours FROM logs WHERE user_id = ? ORDER BY total_hours DESC", (user.id,))
            rows = c.fetchall()
        if rows and rows[0] != (None, None):
            print(rows)
            chunk_size = 10
            chunks = [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]
            for i, chunk in enumerate(chunks):
                embed = discord.Embed(title=f"User Hour Information", description=f"{user.mention}", color=discord.Color.blurple())
                officers_list = ""
                hours_list = ""
                for row in chunk:
                    type = row[0]
                    total_hours = row[1]
                    officers_list += f"{type}\n"
                    hours_list += f"{total_hours/3600:.2f} hours\n"
                embed.add_field(name="Group", value=officers_list, inline=True)
                embed.add_field(name="Hours", value=hours_list, inline=True)
                embed.timestamp = datetime.datetime.now()
                embed.set_footer(text=f"Requested by {interaction.user.name}")
                if i == len(chunks) - 1:
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(title="User Hour Information", description=f"{user.mention} has no clocked hours in this time period!", color=discord.Color.red())
            embed.timestamp = datetime.datetime.now()
            embed.set_footer(text=f"Requested by {interaction.user.name}")
            await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HoursCog(bot))