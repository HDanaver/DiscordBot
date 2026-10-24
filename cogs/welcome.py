############
#   When a user joins, sends a welcome message
############
import os
import discord
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = int(os.getenv('WELCOME_CHANNEL_ID')) if os.getenv('WELCOME_CHANNEL_ID') else None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = self.bot.get_channel(self.channel_id)
        if channel:
            await channel.send(f"Welcome to the Castle, {member.mention}! ")       #Welcome message


async def setup(bot):
    await bot.add_cog(Welcome(bot))