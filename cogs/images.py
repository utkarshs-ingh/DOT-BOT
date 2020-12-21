import praw
import random
import discord.__main__
from discord.ext import commands
from settings import REDDIT_APP_ID, REDDIT_APP_SECRET

class Images (commands.Cog): 
    def __init__(self, bot):
        self.bot = bot
        self.reddit = None
        if REDDIT_APP_ID and REDDIT_APP_SECRET:
            self.reddit = praw.Reddit(client_id=REDDIT_APP_ID, client_secret=REDDIT_APP_SECRET, user_agent="DOT_BOT:%s:1.0" %REDDIT_APP_ID)

    @commands.command()
    async def reddit(self, ctx, sub_reddit: str=""):
        async with ctx.channel.typing():
            if self.reddit:
                default_subreddit = "memes"
                if sub_reddit:
                    default_subreddit = sub_reddit

                submissions = self.reddit.subreddit(default_subreddit).hot()
                post_to_pick = random.randint(1, 51)
                
                for i in range(0, post_to_pick):
                    submission = next(x for x in submissions if not x.stickied)

                if not submission.over_18 or ctx.channel.is_nsfw():
                    await ctx.send(submission.url)
                else:
                    await ctx.send("**NSFW post not allowed here..ಠωಠ**")

            else:
                await ctx.send("No Reddit :(")


def setup(bot):
    bot.add_cog(Images(bot))