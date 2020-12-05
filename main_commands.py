from discord.ext import commands
import os

API_KEY = os.environ.get('DISCORD_API')


bot = commands.Bot(command_prefix="!")

@commands.command()
async def ping(ctx):
    await ctx.send("Pong")

@commands.command(description="Provide name", brief="This is a brief")
async def hello(ctx, *args):
    if len(args) > 0:
        await ctx.send(" ".join(args))
    else:
        await ctx.send("Refer Help...")

bot.add_command(hello)

bot.run(API_KEY)