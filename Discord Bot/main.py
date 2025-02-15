import discord
from discord.ext import commands
import asyncio
from flask import Flask, request, jsonify
import threading
import os
from dotenv import load_dotenv
import datetime
from datetime import timedelta
import sqlite3

load_dotenv()

conn = sqlite3.connect('time.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS clockin
          (user_id INTEGER, type TEXT, start TIMESTAMP)''')
c.execute('''CREATE TABLE IF NOT EXISTS logs
          (user_id INTEGER, clockout TIMESTAMP, seconds INTEGER)''')
conn.commit()

conn.close()

TOKEN = os.getenv("TOKEN")

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

@app.route('/api/check', methods=['GET'])
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
        return
    
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

    if webhook_url:
        return
    
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
        c.execute("DELETE FROM clockin WHERE user_id = ? AND type = ?", (discordId, type,))
        c.execute("INSERT INTO logs VALUES (?, ?, ?)", (discordId, now, seconds))
        conn.commit()
        conn.close()
        bot.loop.create_task(end_dm(discordId, type, formatted_start, formatted_end, seconds))
        return jsonify({"success": "DM logged"}), 200

async def end_dm(discord_id, type, start, end, seconds):
    await bot.wait_until_ready()
    try:
        user = await bot.fetch_user(int(discord_id))
        embed = discord.Embed(title="Clocked Out", color=discord.Color.red())
        embed.add_field(name="Start", value=format_discord_timestamp(start))
        embed.add_field(name="End", value=format_discord_timestamp(end))
        embed.add_field(name="Total Time", value=seconds_converter(seconds))
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