import asyncio
import contextlib
import os

import discord

from .tts import TTSError, synthesize


class GuildPlayer:
    """Holds one guild's voice connection and a sequential speech queue.

    State lives here in memory rather than in the database, the same way a
    live audio player does. Synthesis happens off the queue so playback
    stays in order and one slow clip cannot block another.
    """

    def __init__(self, voice_client: discord.VoiceClient):
        self.vc = voice_client
        self.queue: asyncio.Queue = asyncio.Queue()
        self._task = asyncio.create_task(self._runner())

    async def enqueue(self, text: str, voice: str, rate: str, pitch: str) -> None:
        await self.queue.put((text, voice, rate, pitch))

    def skip(self) -> None:
        if self.vc.is_playing():
            self.vc.stop()  # triggers the after-callback, which advances

    def clear(self) -> None:
        while not self.queue.empty():
            with contextlib.suppress(asyncio.QueueEmpty):
                self.queue.get_nowait()
                self.queue.task_done()
        if self.vc.is_playing():
            self.vc.stop()

    async def stop(self) -> None:
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        if self.vc.is_connected():
            await self.vc.disconnect(force=True)

    async def _runner(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            text, voice, rate, pitch = await self.queue.get()
            try:
                path = await synthesize(text, voice, rate, pitch)
            except TTSError:
                self.queue.task_done()
                continue

            done = asyncio.Event()

            def _after(error, p=path):
                with contextlib.suppress(OSError):
                    os.remove(p)
                loop.call_soon_threadsafe(done.set)

            try:
                self.vc.play(discord.FFmpegOpusAudio(path), after=_after)
            except Exception:
                with contextlib.suppress(OSError):
                    os.remove(path)
                self.queue.task_done()
                continue

            await done.wait()
            self.queue.task_done()


class PlayerManager:
    def __init__(self):
        self.players: dict[int, GuildPlayer] = {}

    def get(self, guild_id: int) -> GuildPlayer | None:
        return self.players.get(guild_id)

    def create(self, voice_client: discord.VoiceClient) -> GuildPlayer:
        player = GuildPlayer(voice_client)
        self.players[voice_client.guild.id] = player
        return player

    async def destroy(self, guild_id: int) -> None:
        player = self.players.pop(guild_id, None)
        if player:
            await player.stop()
