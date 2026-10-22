############
#   When a user joins gives them the BASE_ROLE
#   If a user messages the bot with the PASSWORD, give thems the ELEVATED_ROLE
############
import discord
from discord.ext import commands

class GiveRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.PASSWORD = "abc123"                    # PLACEHOLDER
        self.BASE_ROLE_NAME = "Viewer"
        self.ELEVATED_ROLE_NAME = "Uni victim"      # PLACEHOLDER
        self.GUILD_ID = 1532375961989808210      

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = self.bot.get_guild(self.GUILD_ID)
        role = discord.utils.get(guild.roles, name=self.BASE_ROLE_NAME)     #Welcome message
        await member.add_roles(role)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Ignore messages sent by bots (including this bot)
        if message.author.bot:
            return

        # 2. Only listen to Direct Messages
        if not isinstance(message.channel, discord.DMChannel):
            return

        # 3. Check if the message matches the password
        if message.content.strip() == self.PASSWORD:
            guild = self.bot.get_guild(self.GUILD_ID)
            if not guild:
                await message.channel.send("Error: Server not found.")
                return

            # Retrieve the member object from the server
            member = guild.get_member(message.author.id)
            if not member:
                await message.channel.send("You don't appear to be in the server!")
                return

            role = discord.utils.get(guild.roles, name=self.ELEVATED_ROLE_NAME)
            if not role:
                await message.channel.send(f"Error: The **{self.ELEVATED_ROLE_NAME}** role does not exist.")
                return

            # Avoid re-adding the role if they already verified
            if role in member.roles:
                await message.channel.send("You are already verified!")
                return

            # Grant the role
            await member.add_roles(role)
            await message.channel.send(f"Password correct! You have been granted the **{self.ELEVATED_ROLE_NAME}** role.")
        else:
            await message.channel.send("Incorrect password. Please try again.")


async def setup(bot):
    await bot.add_cog(GiveRole(bot))