from discord.ext import commands
import random as rand

class Gamble (commands.Cog): 
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(brief="Random number 1-100")
    async def roll(self, ctx):
        num = rand.randrange(1, 101)
        await ctx.send(num)

    @commands.command(brief="Do a Dice Roll")
    async def dice(self, ctx):
        num = rand.randrange(1, 6)
        await ctx.send(num)

    @commands.command(brief="Coin Flip")
    async def coin(self, ctx):
        num = rand.choice(["Heads", "Tails"])
        await ctx.send(num)

def setup(bot):
    bot.add_cog(Gamble(bot))