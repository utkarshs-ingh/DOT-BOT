import discord.__main__
from discord.ext import commands
from utils import get_yo_momma_jokes

class NSFW (commands.Cog): 
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def insult(self, ctx, member: discord.Member = None):
        insult = await get_yo_momma_jokes()
        if member is not None:
            await ctx.send("%s %s" %(member.name, insult))
        else:
            await ctx.send("%s %s" %(ctx.message.author.name, insult))

        

def setup(bot):
    bot.add_cog(NSFW(bot))