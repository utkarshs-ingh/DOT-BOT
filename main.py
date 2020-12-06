from discord.ext import commands
from settings import *
import os


bot = commands.Bot(command_prefix="!")

for filename in os.listdir("./cogs"):
    if filename.endswith(".py") and filename != "__init__.py":
        bot.load_extension(f'cogs.{filename[:-3]}')


bot.run(DISCORD_API_KEY)