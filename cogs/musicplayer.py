
import os
import discord
from discord.ext import commands, tasks
import asyncio
import yt_dlp as ytdl
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

#Making Spotify playing possible by it's API

SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

sp = None
if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))
        print("Spotify client initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Spotify client: {e}")

#YTDLP OPTIONS
#Options for title search and playlist extraction
YTDL_SEARCH_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'quiet': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'socket_timeout': 15,
    'retries': 5,
    'extract_flat': 'in_playlist',
}

#Options for streaming audio directly from YouTube url
YTDLP_STREAM_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'nocheckcertificate': True,
    'source_address': '0.0.0.0',
    'socket_timeout': 15,
    'retries': 5,

    'extractor_args':{
        'youtube':{
            'player_client': ['tv_embedded', 'android', 'mweb', 'web']
        }
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl_search = ytdl.YoutubeDL(YTDL_SEARCH_OPTIONS)
ytdl_stream = ytdl.YoutubeDL(YTDLP_STREAM_OPTIONS)

class MusicPlayer(commands.Cog):

    #Initialize the MusicPlayer cog with the bot instance, queues, loop state, and currently playing track information.
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.loop = False
        self.currently_playing = {}

    #Get the queue for a specific guild, initializing it if it doesn't exist.
    def get_queue(self,guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    #Make sure the bot doesn't stuck in the voice channel when the queue is empty, and disconnect it after 5 minutes of inactivity.
    async def auto_disconnect(self, ctx):
        await asyncio.sleep(300)
        if ctx.voice_client and not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            guild_id = ctx.guild.id
            self.get_queue(guild_id).clear()
            self.currently_playing.pop(guild_id, None)
            self.loop.pop(guild_id, None)
            await ctx.voice_client.disconnect()
            await ctx.send("⌛ Inaktivitás miatt kiléptem a hangcsatornából.")

    #Fetch the information from Spotify link
    async def fetch_spotify_tracks(self, url):
        if not sp:
            return None, "A Spotify támogatás nincs beállítva (hiányzik az API kulcs)."
        tracks = []
        try:
            #Check if the URL is a single track
            if 'track' in url:
                track_info = sp.track(url)
                artist = track_info['artists'][0]['name']
                title = track_info['name']
                tracks.append(f"{artist} - {title}")

            #Check if the URL is a playlist
            elif 'playlist' in url:
                results = sp.playlist_items(url)
                items = results['items']
                while results['next']:
                    results = sp.next(results)
                    items.extend(results['items'])

                for item in items:
                    if item.get('track'):
                        artist = item['track']['artists'][0]['name']
                        title = item['track']['name']
                        tracks.append(f"{artist} - {title}")

            #Check if the URL is an album
            elif 'album' in url:
                results = sp.album_tracks(url)
                items = results['items']
                while results['next']:
                    results = sp.next(results)
                    items.extend(results['items'])

                for item in items:
                    artist = item['artists'][0]['name']
                    title = item['name']
                    tracks.append(f"{artist} - {title}")
            return tracks, None
        except Exception as e:
            return None, f"Hiba történt a Spotify link feldolgozása közben: {e}"

    
async def setup(bot):
    await bot.add_cog(MusicPlayer(bot))

        
    