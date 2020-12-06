from discord.ext import commands

class Basic (commands.Cog): 
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, ex):
        print(ex)
        await ctx.send("**Invalid usage of command**")
    
    @commands.command()
    @commands.guild_only()
    async def invite(self, ctx):
        invite_link = await ctx.channel.create_invite(max_age=10)
        await ctx.send(invite_link)

def setup(bot):
    bot.add_cog(Basic(bot))