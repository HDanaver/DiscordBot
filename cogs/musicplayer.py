
import os
import discord
from discord.ext import commands, tasks
import asyncio
import yt_dlp as ytdl
import spotipy
import random
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
        self.loop = {}
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

    #Play the next track
    async def play_next(self, ctx):
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        is_looped = False

        if self.loop.get(guild_id, False) and guild_id in self.currently_playing:
            next_track = self.currently_playing[guild_id]
            is_looped = True
        elif queue:
            next_track = queue.pop(0)
            self.currently_playing[guild_id] = next_track
        else:
            self.currently_playing.pop(guild_id, None)
            await ctx.send("✅ A Queue üres.", delete_after=60)
            await self.auto_disconnect(ctx)
            return

        try:
            webpage_url = next_track.get('url')
            loop= asyncio.get_running_loop()

            if not webpage_url.startswith('http://') and not webpage_url.startswith('https://'):
                search_data = await loop.run_in_executor(None, lambda: ytdl_search.extract_info(f"ytsearch:{webpage_url}", download=False))
                if search_data and 'entries' in search_data and search_data['entries']:
                    first_video = search_data['entries'][0]
                    webpage_url = first_video.get('webpage_url') or f"https://www.youtube.com/watch?v={first_video.get('id')}"
                    next_track['title'] = first_video.get('title', next_track['title'])

            data = await loop.run_in_executor(None,lambda: ytdl_stream.extract_info(webpage_url, download=False))

            if 'entries' in data and data['entries']:
                data = data['entries'][0]

            stream_url = data['url']
        except Exception as e:
            print(f"Hiba történt a következő szám lejátszása közben: {e}")
            await ctx.send(f"❌ Hiba történt a következő szám lejátszása közben: {e}", delete_after=20)
            await self.play_next(ctx)
            return

        source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)

        ctx.voice_client.play(
            source,
            after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
        )

        if not is_looped:
            await ctx.send(f"🎶 Most szól: **{next_track['title']}**")

    #Making sure the bot is only playing music from the channels that were meant for music, and not from any other channels.
    async def cog_before_invoke(self,ctx):

        channel_name = ctx.channel.name.lower()

        if "zene" not in channel_name and "music" not in channel_name:
            await ctx.send("❌ A zene parancsokat csak olyan csatornában használhatod ami zene lejátszására van fenntartva.", delete_after=20)
            raise commands.CheckFailure("A parancsot nem a megfelelő nevű csatornában hívták meg.")

    #Making play command, that can play music from YouTube and Spotify links, or search for a song by title.
    @commands.command(name="play", help="Lejátszik egy számot vagy playlistet a megadott YouTube vagy SoundCloud linkről, vagy keres egy számot a megadott címmel.")
    async def play(self , ctx, *, search: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Csatlakoznod kell egy hangcsatornához a zene lejátszásához.", delete_after=20)

        channel = ctx.author.voice.channel
        if not ctx.voice_client:
            await channel.connect()
        elif ctx.voice_client.channel != channel:
            await ctx.voice_client.move_to(channel)

        async with ctx.typing():
            queue = self.get_queue(ctx.guild.id)
            loop = asyncio.get_running_loop()

        #Handle Spotify links
            if "spotify.com" in search:
                #Spotify playlist and album checking
                if "playlist" in search or "album" in search:
                    await ctx.send("🔄 Spotify playlist vagy album linket kaptam, feldolgozás...")
                    spotify_tracks, error = await self.fetch_spotify_tracks(search)
                    if error:
                        await ctx.send(f"❌ Hiba történt a Spotify link feldolgozása közben: {error}", delete_after=20)
                        return

                    track_count = len(spotify_tracks)

                    if track_count > 1:
                        await ctx.send(f"❓ Ez a Spotify hivatkozás **{track_count}** dalt tartalmaz. Biztosan hozzá akarod adni a sorhoz? Írd be: **yes** vagy **no** (60 másodperced van).")

                    #Function for checking the user's response to the confirmation prompt
                    def check(m: discord.Message):
                        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", 'y','igen', 'no', 'n', 'nem']

                    try:
                        msg = await self.bot.wait_for('message', check=check, timeout=60)
                        if msg.content.lower() not in ["yes", 'y','igen']:
                            return await ctx.send("🚫 Lejátszási lista hozzáadása megszakítva.")

                    except asyncio.TimeoutError:
                        return await ctx.send("⏰ Időtúllépés. A lejátszási lista hozzáadása megszakítva.", delete_after=20)

                    added_songs = [{'url': track_name, 'title': track_name, 'locked': False}for track_name in spotify_tracks]
                    queue.extend(added_songs)
                    await ctx.send(f"✅ **{track_count}** szám hozzáadva a sorhoz a Spotify link alapján.")

                else:
                    #Single Spotify track handling
                    spotify_tracks, error = await self.fetch_spotify_tracks(search)
                    if error:
                        return await ctx.send(f"❌ Hiba történt a Spotify link feldolgozása közben: {error}", delete_after=20)

                    song_info = {'url': spotify_tracks[0], 'title': spotify_tracks[0], 'locked' : False}
                    queue.append(song_info)
                    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                        await ctx.send(f"✅ **{song_info['title']}** hozzáadva a sorhoz a Spotify link alapján.")
            
            #Handle YouTube links and search queries and SoundCloud
            else:
                is_url = search.startswith("http://") or search.startswith("https://")
                query = search if is_url else f"ytsearch:{search}"

                data = await loop.run_in_executor(None, lambda:ytdl_search.extract_info(query, download=False))

                if not data:
                    return await ctx.send("❌ Nem található a keresett zene.")

                #Playlist Handling
                if is_url and 'entries' in data and data['entries']:
                    raw_entries = [e for e in data['entries'] if e]
                    track_count = len(raw_entries)

                    if track_count == 0:
                        return await ctx.send("❌ Nem sikerült dalt kinyerni a hivatkozásból.", delete_after=20)
                    
                    is_radio = "start_radio=1" in search or "radio=1" in search
                    link_type = "rádió/mix" if is_radio else "lejátszási lista"

                    await ctx.send(f"❓ Ez a YouTube {link_type} **{track_count}** dalt tartalmaz. Biztosan hozzá akarod adni a sorhoz? Írd be: **yes** vagy **no** (60 másodperced van).")

                    def check(m: discord.Message):
                        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['yes', 'y', 'igen', 'no', 'n', 'nem']

                    try:
                        msg = await self.bot.wait_for('message', check=check, timeout=60)
                        if msg.content.lower() not in ['yes', 'y', 'igen']:
                            return await ctx.send(f"🚫 A hozzáadás megszakítva.",delete_after = 20)
                    except asyncio.TimeoutError:
                        return await ctx.send(f"⏱️ Időtúllépés! A dalok nem lettek hozzáadva a sorhoz.", delete_after = 20)

                    added_songs = []
                    for entry in raw_entries:
                        song_url = entry.get('webpage_url') or entry.get('url') or (f"https://www.youtube.com/watch?v={entry['id']}" if entry.get('id') else None)
                        title = entry.get('title', 'Ismeretlen cim')
                        if song_url:
                            added_songs.append({'url': song_url, 'title': title, 'locked': False})

                    queue.extend(added_songs)
                    await ctx.send(f"✅ Hozzáadva a sorhoz: **{len(added_songs)}** dal.")

                #Simple Tracks and Single URL
                else:
                    if not is_url and 'entries' in data and data['entries']:
                        data = data['entries'][0]

                    song_url = data.get('webpage_url') or data.get('original_url') or search
                    title = data.get('title', search)
                    song_info = {'url': song_url, 'title': title, 'locked': False}
                    queue.append(song_info)

                    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                        await ctx.send(f"✅ Hozzáadva a sorhoz (**#{len(queue)}**): **{title}**")

            if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                await self.play_next(ctx)

    #Skip function        
    @commands.command(name = 'skip', help= 'A következő dal lejátszása a sorban')
    async def skip(self, ctx):
        if not ctx.voice_client or not (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            return await ctx.send("❌ Nincs lejátszás alatt álló zene, amit át lehetne ugrani.")

        self.loop[ctx.guild.id] = False
        ctx.voice_client.stop()
        await ctx.send("⏭️ **A dal átugorva!**")

    #Pause function
    @commands.command(name='pause', help= 'Megállítja a jelenleg lejátszott dalt')
    async def pause(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            return await ctx.send("❌ Nincs lejátszás alatt álló zene, amit meg lehetne állítani.")

        ctx.voice_client.pause()
        await ctx.send("⏸️ **A dal megállítva!**")

    #Resume function
    @commands.command(name='resume', aliases=['start', 'continue', 'cunt'], help='Folytatja a megállított dalt')
    async def resume(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_paused():
            return await ctx.send("❌ Nincs megállított zene, amit folytatni lehetne.")

        ctx.voice_client.resume()
        await ctx.send("▶️ **A dal folytatva!**")

    #Stop function
    @commands.command(name='stop', help='Megállítja a lejátszást és kiüríti a sort')
    async def stop(self, ctx):
        if not ctx.voice_client:
            return await ctx.send("❌ A bot nincs csatlakozva egy hangcsatornához sem.")

        guild_id = ctx.guild.id
        self.get_queue(guild_id).clear()
        self.loop[guild_id] = False
        self.currently_playing.pop(guild_id, None)

        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            ctx.voice_client.stop()

        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ **Leállítottam a zenét, töröltem a sort és kiléptem.**")

    #Loop function
    @commands.command(name='loop', help='A jelenlegi dal ismétlésének ki/bekapcsolása')
    async def loop(self, ctx):
        guild_id = ctx.guild.id
        state = self.loop[guild_id] = not self.loop.get(guild_id, False)
        status_text = "BEKAPCSOLVA" if state else "KIKAPCSOLVA"
        await ctx.send(f"🔁 **A dal ismétlése: {status_text}.**")

    #Queue list function
    @commands.command(name='queue', aliases=['q'], help= 'Megjeleníti a jelenlegi lejátszási sort')
    async def queue_info(self, ctx):
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        current = self.currently_playing.get(guild_id)

        if not current and not queue:
            return await ctx.send("❌ A lejátszási sor üres.")

        embed = discord.Embed(title="🎵 Lejátszási sor", color=discord.Color.green())

        if current and ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            loop_status = "🔂 *(Ismétlés BE)*" if self.loop.get(guild_id, False) else ""
            embed.add_field(name='▶️ Most szól:', value=f"**{current['title']}**{loop_status}", inline=False)

        if queue:
            song_list = "\n".join([f"**{i}.** {song['title']}" for i, song in enumerate(queue[:10], start=1)])
            if len(queue) > 10:
                song_list += f"\n... és még **{len(queue) - 10}** dal a sorban."
            embed.add_field(name="📋 Következő zenék:", value=song_list, inline=False)
        else:
            embed.add_field(name="📋 Következő zenék:", value="*Nincs több zene a sorban.*", inline=False)

        await ctx.send(embed=embed)

    #Prioritize function
    @commands.command(name='makefirst', aliases=['mf', 'top'], help= 'Egy már a sorban lévő dalt a sor elejére teszi és zárolja cím alapján.')
    async def makefirst(self, ctx, *, search_title: str):
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)

        if not queue:
            return await ctx.send("❌ A lejátszási sor üres, nincs mit előre tenni.")

        found_song = None
        found_index = -1

        for i, song in enumerate(queue):
            if search_title.lower() in song['title'].lower():
                found_song = song
                found_index = i
                break

        if not found_song:
            return await ctx.send(f"❌ Nem találtam ilyen dalt a sorban: **{search_title}**")

        queue.pop(found_index)
        
        found_song['locked']=True
        
        queue.insert(0, found_song)

        await ctx.send(f"🔒 **{found_song['title']}** átkerült a lejátszási sor **elejére**, és zárolva lett!")

    #Randomize Queue function
    @commands.command(name='shuffle', aliases=['sh','random','r'], help='A lejátszási sor összekeverése')
    async def shuffle(self,ctx):
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)


        if not queue or len(queue) < 2:
            return await ctx.send("❌ A lejátszási sor üres, nincs mit összekeverni.")

        locked_songs = [song for song in queue if song.get('locked', False)]
        unlocked_songs = [song for song in queue if not song.get('locked', False)]

        if not unlocked_songs:
            return await ctx.send("❌ Minden dal zárolva van a sorban, nincs mit keverni.")

        random.shuffle(unlocked_songs)
        self.queues[guild_id] = locked_songs + unlocked_songs
        await ctx.send("🔀 A lejátszási sor összekeverve!")

    

async def setup(bot):
    await bot.add_cog(MusicPlayer(bot))

        
    