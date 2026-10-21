import discord
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        WELCOME_CHANNEL_ID = 1532376640909213756    # Replace with your welcome channel ID
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            await channel.send(f'Welcome to the Castle, {member.mention}!')

        

async def setup(bot):
    await bot.add_cog(Welcome(bot))