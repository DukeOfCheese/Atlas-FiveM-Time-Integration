import discord
from discord import Webhook
from discord.ext import commands
import asyncio
from flask import Flask, request, jsonify
import threading
import os
from dotenv import load_dotenv
import datetime
from datetime import timedelta
import sqlite3
import tracemalloc
from typing import Optional, Literal
import requests

tracemalloc.start()
load_dotenv()

conn = sqlite3.connect('time.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS clockin
          (user_id INTEGER, type TEXT, start TIMESTAMP)''')
c.execute('''CREATE TABLE IF NOT EXISTS logs
          (user_id INTEGER, type TEXT, clockout TIMESTAMP, seconds INTEGER)''')
conn.commit()

conn.close()

TOKEN = os.getenv("TOKEN")
OWNER_DISCORD_ID = os.getenv("OWNER_DISCORD_ID")

def format_discord_timestamp(datetime_str):
    try:
        dt_object = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        unix_timestamp = int(dt_object.timestamp())
        return f"<t:{unix_timestamp}:R>"
    except ValueError as e:
        return f"Invalid datetime string: {e}"
    
def seconds_converter(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    time_parts = []
    if hours > 0:
        time_parts.append(f"{hours:.0f} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        time_parts.append(f"{minutes:.0f} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not time_parts:
        time_parts.append(f"{seconds:.0f} second{'s' if seconds != 1 else ''}")
    
    return " ".join(time_parts)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=".", intents=intents)
app = Flask(__name__)

@bot.event
async def setup_hook():
    print("------")
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    cogs = ["hours"]
    for cog in cogs:
        try:
            await bot.load_extension(name=f"cogs.{cog}")
            print(f"Loaded {cog}\n------")
        except Exception as e:
            print(e)
    print("Loaded cogs")
    print("------")

@bot.command()
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    if ctx.author.id == int(OWNER_DISCORD_ID):
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            if spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()
            await ctx.send(f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}", ephemeral=True)
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1
        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}", ephemeral=True)
    else:
        return

@app.route('/', methods=['GET'])
def api_test():
    return {"check": "pass"}

@app.route('/api/time/start', methods=['POST'])
def time_start():
    data = request.get_json()

    required_fields = ['discordId', 'type']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400
    
    discordId = data.get('discordId')
    type = data.get('type')
    webhook_url = data.get('webhookUrl')

    if webhook_url:
        data = {
            "username": "Atlas Time Integration",
            "embeds": [
            {
                "title": "Clock-In Alert",
                "description": "A user has clocked in.",
                "color": 0x00ff00,
                "fields": [
                    {"name": "Start", "value": format_discord_timestamp(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')), "inline": True},
                    {"name": "User", "value": f"<@{discordId}>", "inline": True},
                    {"name": "Type", "value": type, "inline": False},
                ],
                "footer": {"text": "Atlas Time Integration"},
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }
        ]
        }
        requests.post(webhook_url, json=data)
    
    now = datetime.datetime.now()
    
    conn = sqlite3.connect('time.db')
    c = conn.cursor()

    c.execute("SELECT * FROM clockin WHERE user_id = ? AND type = ?", (discordId, type,))
    row = c.fetchone()
    if row:
        return ({"error": "User is clocked in to this type already"}), 417
    else:
        c.execute("INSERT INTO clockin VALUES (?, ?, ?)", (discordId, type, now,))
        conn.commit()
        
        conn.close()
        return ({"success": "User is now clocked in"}), 200

@app.route('/api/time/end', methods=['POST'])
def time_end():
    data = request.get_json()

    required_fields = ['discordId', 'type']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400
    
    discordId = data.get('discordId')
    type = data.get('type')
    webhook_url = data.get('webhookUrl')
    
    conn = sqlite3.connect('time.db')
    c = conn.cursor()

    c.execute("SELECT * FROM clockin WHERE user_id = ? AND type = ?", (discordId, type,))
    row = c.fetchone()
    if not row:
        return ({"error": "User is not clocked"})
    else:
        now = datetime.datetime.now()
        row_datetime = datetime.datetime.fromisoformat(row[2])
        formatted_start = row_datetime.strftime('%Y-%m-%d %H:%M:%S')
        formatted_end = now.strftime('%Y-%m-%d %H:%M:%S')
        time_taken = now - row_datetime
        seconds = time_taken.total_seconds()
        total_time = seconds_converter(seconds)
        c.execute("DELETE FROM clockin WHERE user_id = ? AND type = ?", (discordId, type,))
        c.execute("INSERT INTO logs VALUES (?, ?, ?, ?)", (discordId, type, now, seconds))
        conn.commit()
        conn.close()

        if webhook_url:
            data = {
                "username": "Atlas Time Integration",
                "embeds": [
                {
                    "title": "Clock-Out Alert",
                    "description": "A user has clocked out.",
                    "color": 0xFF0000,
                    "fields": [
                        {"name": "Start", "value": format_discord_timestamp(formatted_start), "inline": True},
                        {"name": "End", "value": format_discord_timestamp(formatted_end), "inline": True},
                        {"name": "User", "value": f"<@{discordId}>", "inline": True},
                        {"name": "Type", "value": type, "inline": True},
                        {"name": "Total Time", "value": total_time, "inline": True}
                    ],
                    "footer": {"text": "Atlas Time Integration"},
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
                }
            ]
            }
        requests.post(webhook_url, json=data)
        future = asyncio.run_coroutine_threadsafe(end_dm(discordId, type, formatted_start, formatted_end, total_time), bot.loop)
        return jsonify({"success": "DM logged"}), 200

async def end_dm(discord_id, type, start, end, time):
    await bot.wait_until_ready()
    try:
        user = await bot.fetch_user(int(discord_id))
        embed = discord.Embed(title="Clocked Out", color=discord.Color.red())
        embed.add_field(name="Start", value=format_discord_timestamp(start))
        embed.add_field(name="End", value=format_discord_timestamp(end))
        embed.add_field(name="Total Time", value=time)
        embed.add_field(name="User", value=f"<@{discord_id}>")
        embed.add_field(name="Group", value=type)
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(text="Atlas Time Integration")
        await user.send(embed=embed)
    except Exception as e:
        print(f"Error sending DM: {e}")

def run_flask():
    app.run(host="0.0.0.0", port=4000)

threading.Thread(target=run_flask, daemon=True).start()

bot.run(TOKEN)