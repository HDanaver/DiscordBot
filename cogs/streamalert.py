import discord
import os
import aiohttp
from discord.ext import commands, tasks

class StreamAlert(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.client_id = os.getenv('TWITCH_CLIENT_ID')
        self.client_secret = os.getenv('TWITCH_CLIENT_SECRET')

        self.twitch_username = os.getenv('TWITCH_USERNAME')  # Replace with your Twitch username
        self.discord_channel_id = int(os.getenv('ALERT_CHANNEL_ID')) if os.getenv('ALERT_CHANNEL_ID') else None  # Replace with your Discord channel ID for stream alerts

        self.access_token = None
        self.is_live = False 

        self.check_twitch_stream.start()  # Start the background task to check Twitch stream status

    def cog_unload(self):
        self.check_twitch_stream.cancel()  # Cancel the background task when the cog is unloaded

    async def get_twitch_access_token(self):
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data.get("access_token")
                    print("Access token obtained:", self.access_token)
                else:
                    print("Failed to obtain access token.")

    async def check_twitch_stream_status(self):
        if not self.access_token:
            await self.get_twitch_access_token()

        url = f"https://api.twitch.tv/helix/streams?user_login={self.twitch_username}"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:

                if response.status == 401:
                    await self.get_twitch_access_token()
                    return await self.check_twitch_stream_status()

                if response.status == 200:
                    data = await response.json()
                    streams = data.get("data", [])
                    return streams[0] if streams else None
                else:
                    print("Failed to check Twitch stream status.")
                    return None

    @tasks.loop(minutes=3.0)
    async def check_twitch_stream(self):
        stream_data = await self.check_twitch_stream_status()

        if stream_data and not self.is_live:
            self.is_live = True

            channel = self.bot.get_channel(self.discord_channel_id) or await self.bot.fetch_channel(self.discord_channel_id)
            if channel:
                stream_title = stream_data.get("title", "No Title")
                stream_url = f"https://www.twitch.tv/{self.twitch_username}"
                await channel.send(f"🔴 {self.twitch_username} is now live on Twitch!\nTitle: {stream_title}\nWatch here: {stream_url}")

        elif not stream_data and self.is_live:
            self.is_live = False
            print(f"{self.twitch_username} is no longer live on Twitch.")

    @check_twitch_stream.before_loop
    async def before_check_twitch_stream(self):
        await self.bot.wait_until_ready()  # Wait until the bot is ready before starting the loop

async def setup(bot):
    await bot.add_cog(StreamAlert(bot))