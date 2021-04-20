import asyncio
import datetime as dt
import random
import re
import typing as t
from enum import Enum
import pickle

import discord
import wavelink
from discord.ext import commands
from utils import save_data, savedPlaylists, loadPlaylists

OPTIONS = {
    "1️⃣": 0,
    "2⃣": 1,
    "3⃣": 2,
    "4⃣": 3,
    "5⃣": 4,
}


class AlreadyConnectedToChannel(commands.CommandError):
    pass


class NoVoiceChannel(commands.CommandError):
    pass


class QueueIsEmpty(commands.CommandError):
    pass


class NoTracksFound(commands.CommandError):
    pass


class PlayerIsAlreadyPaused(commands.CommandError):
    pass

class PlayerIsAlreadyPlaying(commands.CommandError):
    pass


class NoMoreTracks(commands.CommandError):
    pass


class NoPreviousTracks(commands.CommandError):
    pass


class InvalidRepeatMode(commands.CommandError):
    pass

class NoNamePlaylist(commands.CommandError):
    pass


class RepeatMode(Enum):
    NONE = 0
    ONE = 1
    ALL = 2


class Queue:
    def __init__(self):
        self._queue = []
        self.position = 0
        self.repeat_mode = RepeatMode.NONE

    @property
    def is_empty(self):
        return not self._queue

    @property
    def current_track(self):
        if not self._queue:
            raise QueueIsEmpty

        if self.position <= len(self._queue) - 1:
            return self._queue[self.position]

    @property
    def upcoming(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[self.position + 1:]

    @property
    def history(self):
        if not self._queue:
            raise QueueIsEmpty
        
        return self._queue[:self.position]

    @property
    def length(self):
        return len(self._queue)

    def add(self, *args):
        self._queue.extend(args)

    def get_next_track(self):
        if not self._queue:
            raise QueueIsEmpty

        self.position += 1

        if self.position < 0:
            return None
        elif self.position > len(self._queue) - 1:
            if self.repeat_mode == RepeatMode.ALL:
                self.position = 0
            else:
                return None
        
        return self._queue[self.position]
    
    @property
    def all_tracks(self):
        if not self._queue:
            raise QueueIsEmpty        
        return self._queue[::]
    
    def shuffle(self):
        if not self._queue:
            raise QueueIsEmpty

        upcoming = self.upcoming
        random.shuffle(upcoming)
        self._queue = self._queue[:self.position + 1]
        self._queue.extend(upcoming)

    def set_repeat_mode(self, mode):
        if mode == 'none':
            self.repeat_mode = RepeatMode.NONE
        elif mode == '1':
            self.repeat_mode = RepeatMode.ONE
        else:
            self.repeat_mode = RepeatMode.ALL

    def empty(self):
        self._queue.clear()
        self.position = 0



class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = Queue()

    async def connect(self, ctx, channel=None):
        if self.is_connected:
            raise AlreadyConnectedToChannel

        if (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            raise NoVoiceChannel

        await super().connect(channel.id)
        return channel

    async def teardown(self):
        try:
            await self.destroy()
        except KeyError:
            pass

    async def add_tracks(self, ctx, tracks):
        if not tracks:
            raise NoTracksFound

        if isinstance(tracks, wavelink.TrackPlaylist):
            self.queue.add(*tracks.tracks)
        elif len(tracks) == 1:
            self.queue.add(tracks[0])
            await ctx.send(f"Added {tracks[0].title} to the queue.")
        else:
            if(track := await self.choose_track(ctx, tracks)) is not None:
                self.queue.add(track)
                await ctx.send(f"Added {track.title} to the queue.")

        if not self.is_playing and not self.queue.is_empty:
            await self.start_playback()

    async def choose_track(self, ctx, tracks):
        def react_check(r, u):
            return (r.emoji in OPTIONS.keys() and u == ctx.author and r.message.id == msg.id)

        embed = discord.Embed(
            title="Choose a song",
            description=(
                "\n".join(
                    f"**{i+1}.** {t.title} ({t.length//60000}:{str(t.length%60).zfill(2)})"
                    for i, t in enumerate(tracks[:5])
                )
            ),
            colour=ctx.author.colour,
            timestamp=dt.datetime.utcnow()
        )
        embed.set_author(name="Query Results")
        embed.set_footer(text=f"{ctx.author.display_name} Summoned the DJ", icon_url=ctx.author.avatar_url)

        msg = await ctx.send(embed=embed)
        for emoji in list(OPTIONS.keys()):
            await msg.add_reaction(emoji)

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=5.0, check=react_check)
        except asyncio.TimeoutError:
            await msg.delete()
            return tracks[0]
        else:
            await msg.delete()
            return tracks[OPTIONS[reaction.emoji]]

    async def start_playback(self):
        await self.play(self.queue.current_track)

    async def advance(self):
        try:
            if (track := self.queue.get_next_track()) is not None:
                await self.play(track)
        except QueueIsEmpty:
            pass

    async def repeat_track(self):
        await self.play(self.queue.current_track)

    async def all_track(self, ctx):
        return self.queue.all_tracks
    
    async def upcoming_tracks(self, ctx):
        if self.queue.is_empty:
            raise QueueIsEmpty

        tracks = self.queue.upcoming
        title = "Upcoming :musical_note:"
        description =  "\n".join(f'**{i+1}.** {t.title}' for i, t in enumerate(tracks[::]))
        if not len(tracks): 
            title = ""
            description = "**Queue is empty :scream:**"
        embed = discord.Embed(
            title=title,
            description=description,
            colour=ctx.author.colour
        )

        embed.add_field(name="Currently Playing", value=self.queue.current_track.title, inline=False)

        await ctx.send(embed=embed)


class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot):
        self.bot = bot
        self.wavelink = wavelink.Client(bot=bot)
        self.bot.loop.create_task(self.start_nodes())

    # Move to next track or repeat the same
    @wavelink.WavelinkMixin.listener("on_track_end") 
    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self, node, payload):
        if payload.player.queue.repeat_mode == RepeatMode.ONE:
            await payload.player.repeat_track()
        else:
            await payload.player.advance()


    async def start_nodes(self):
        await self.bot.wait_until_ready()

        nodes = {
            "MAIN": {
                "host": "ibm-sprint.herokuapp.com",
                "port": 80,
                "rest_uri": "http://ibm-sprint.herokuapp.com:80",
                "password": "youshallnotpass",
                "identifier": "MAIN",
                "region": "europe",
                "heartbeat": float(10000000),
            }
        }

        for node in nodes.values():
            await self.wavelink.initiate_node(**node)

    def get_player(self, obj):
        if isinstance(obj, commands.Context):
            return self.wavelink.get_player(obj.guild.id, cls=Player, context=obj)
        elif isinstance(obj, discord.Guild):
            return self.wavelink.get_player(obj.id, cls=Player)

    @commands.command(name="connect", aliases=["join", "cc"])
    async def connect_command(self, ctx, *, channel: t.Optional[discord.VoiceChannel]):
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise NoVoiceChannel

        player = self.get_player(ctx)
        await ctx.send(f'DJ DOT connecting to **`{channel.name}`**')
        await player.connect(ctx)

    @commands.command(name="disconnect", aliases=["leave", "dc"])
    async def disconnect_command(self, ctx):
        player = self.get_player(ctx)
        
        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            raise NoVoiceChannel
        finally:
            if player.channel_id != channel.id:
                raise NoVoiceChannel
        
        await ctx.send(f'DJ DOT left **`{channel.name}`**')
        await player.destroy() # ask if user want to save playlist or completly remove all instances
        # await player.disconnect()      

    @commands.command(name="play", aliases=["pl"])
    async def play_command(self, ctx, *, query: t.Optional[str]):
        player = self.get_player(ctx)
        
        if not player.is_connected:
            await player.connect(ctx)
        
        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            raise NoVoiceChannel

        if player.channel_id != channel.id:
            raise NoVoiceChannel

        if query is None:
            if player.queue.is_empty:
                raise QueueIsEmpty

            if not player.is_paused:
                raise PlayerIsAlreadyPlaying

            await player.set_pause(False)
            await ctx.send("Playback resumed :play_pause:")

        else:
            await player.add_tracks(ctx, await self.wavelink.get_tracks(f"ytsearch:{query}"))

    @commands.command(name="loadplaylist", aliases=["loadpl"])
    async def loadplaylist_command(self, ctx, *, listname: str=""):
        player = self.get_player(ctx)
        
        if not player.is_connected:
            await player.connect(ctx)
        
        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            raise NoVoiceChannel

        if player.channel_id != channel.id:
            raise NoVoiceChannel
       
        if len(listname) == 0:
            savedlists = await savedPlaylists(ctx.author.id)
            if len(savedlists) == 0:
                raise QueueIsEmpty

            embed = discord.Embed(
                title=f'Saved Playlists by:   **`{ctx.author.display_name}`**',
                description=(
                "\n".join(
                        f"**{i+1}.** {t}"
                        for i, t in enumerate(savedlists)
                    )
                ),
                colour=ctx.author.colour
            )
            await ctx.send(embed=embed)

        else:
            query = await loadPlaylists(ctx.author.id, listname)
            if len(query) == 0:
                raise QueueIsEmpty

            for playlistTracks in query:
                await player.add_tracks(ctx, await self.wavelink.get_tracks(playlistTracks))
        
    
    @commands.command(name="saveplaylist", aliases=["savepl"])
    async def saveplaylist_command(self, ctx, *, listname: str=""):
        player = self.get_player(ctx)
        
        if not player.is_connected:
            await player.connect(ctx)
        
        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            raise NoVoiceChannel

        if player.channel_id != channel.id:
            raise NoVoiceChannel

        query = await player.all_track(ctx)
        if len(listname) == 0:
            raise NoNamePlaylist

        savelist = []
        for playlistTracks in query:
            savelist.append(playlistTracks.uri)
        
        if not len(savelist) == 0:
            await save_data(ctx.author.id, listname, savelist)
        else:
            raise NoMoreTracks
            

    @commands.command(name="playlist", aliases=["list", "ll"])
    async def display_queue(self, ctx):
        player = self.get_player(ctx)
        await player.upcoming_tracks(ctx)

    @commands.command(name="pause", aliases=["ps"])
    async def pause_command(self, ctx):
        player = self.get_player(ctx)
        if player.is_paused:
            raise PlayerIsAlreadyPaused
             
        await player.set_pause(True)
        await ctx.send("Playback Paused :pause_button:")

    @commands.command(name="stop", aliases=["sp"])
    async def stop_command(self, ctx):
        player = self.get_player(ctx)
        player.queue.empty()
        await player.stop()
        await ctx.send("Playback Stopped")

    @commands.command(name="next", aliases=["nx", "nxt"])
    async def next_track_command(self, ctx):
        player = self.get_player(ctx)

        if not player.queue.upcoming:
            raise NoMoreTracks

        await player.stop()
        await ctx.send(f'Playing Next Track :track_next:  {player.queue.upcoming[0]}')

    @commands.command(name="previous", aliases=["pr", "pre"])
    async def previous_track_command(self, ctx):
        player = self.get_player(ctx)

        if not player.queue.history:
            raise NoPreviousTracks

        player.queue.position -= 2
        await player.stop()
        await ctx.send(f'Playing Previous Track :track_previous:')


    @commands.command(name="shuffle", aliases=["mix"])
    async def shuffle_track_command(self, ctx):
        player = self.get_player(ctx)
        if not player.queue.upcoming:
            raise NoMoreTracks
        player.queue.shuffle()
        await ctx.send("Shuffled Upcoming Tracks")

    @commands.command(name="repeat", aliases=["rt"])
    async def repeat_track_command(self, ctx, mode: str):
        if mode not in ('1', 'none', 'all'):
            raise InvalidRepeatMode

        player = self.get_player(ctx)
        player.queue.set_repeat_mode(mode)
        rep = ":repeat:"
        if mode == "1":
            rep = ":repeat_one:"
        await ctx.send(f"Repeat mode set to {mode} {rep}")
        
    @disconnect_command.error
    async def disconnect_command_error(self, ctx, exc):
        if isinstance(exc, NoVoiceChannel):
            await ctx.send("No suitable voice channel was provided.")
        
    @play_command.error
    async def play_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("**Queue is empty :scream:**")
        elif isinstance(exc, NoVoiceChannel):
            await ctx.send("No suitable voice channel was provided.")
        elif isinstance(exc, PlayerIsAlreadyPlaying):
            await ctx.send("** Playback is already playing :confused:**")

    @saveplaylist_command.error
    async def saveplaylist_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("**Queue is empty :scream:**")
        elif isinstance(exc, NoVoiceChannel):
            await ctx.send("No suitable voice channel was provided.")
        elif isinstance(exc, NoNamePlaylist):
            await ctx.send("**Please provide a playlist name :confused:**")

    @loadplaylist_command.error
    async def loadplaylist_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("**Queue is empty :scream:**")
        elif isinstance(exc, NoVoiceChannel):
            await ctx.send("No suitable voice channel was provided.")
        elif isinstance(exc, NoNamePlaylist):
            await ctx.send("**Please provide a playlist name :confused:**")

    @display_queue.error
    async def display_queue_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("**Queue is empty :scream:**")

    @pause_command.error
    async def pause_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPaused):
            await ctx.send("** Playback is already paused :confused:**")

    @next_track_command.error
    async def next_track_command_error(self, ctx, exc):
        if isinstance(exc, NoMoreTracks):
            await ctx.send("**No more tracks to play :confounded:**")
        elif isinstance(exc, QueueIsEmpty):
            await ctx.send("**No more tracks to play :confounded:**")

    @previous_track_command.error
    async def previous_track_command_error(self, ctx, exc):
        if isinstance(exc, NoPreviousTracks):
            await ctx.send("**No more tracks to play :confounded:**")
        elif isinstance(exc, QueueIsEmpty):
            await ctx.send("**No more tracks to play :confounded:**")

    @shuffle_track_command.error
    async def shuffle_track_command_error(self, ctx, exc):
        if isinstance(exc, NoMoreTracks):
            await ctx.send("**No more tracks to shuffle  :rolling_eyes:**")

    @repeat_track_command.error
    async def repeat_track_command_error(self, ctx, exc):
        if isinstance(exc, InvalidRepeatMode):
            await ctx.send("**Please choose from 1/none/all  :rolling_eyes:**")
            


def setup(bot):
    bot.add_cog(Music(bot))
