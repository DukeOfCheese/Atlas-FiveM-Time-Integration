import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import datetime
import tracemalloc
from typing import Optional, Literal

tracemalloc.start()
load_dotenv()

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

class MyBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tree = Tree() #type: ignore  # noqa: F821

@bot.event
async def setup_hook():
    print("------")
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    cogs = ["noti", "hours"]
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

bot.run(TOKEN)