
import discord
from discord.ext import commands, tasks
import asyncio


class MusicPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = {}
        self.loop = False
        self.currently_playing = {}
     
                
async def setup(bot):
    await bot.add_cog(MusicPlayer(bot))

        
    