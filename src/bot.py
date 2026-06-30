import traceback

import discord
from discord import app_commands
from discord.ext import commands

from . import config, embeds
from .db import get_guild_config, get_pronunciations, get_user_voice, init_db
from .services.clean import normalize
from .services.player import PlayerManager

INTENTS = discord.Intents.default()
INTENTS.message_content = True  # privileged: required to read messages to speak
INTENTS.members = True          # privileged: nicer mention/name resolution
INTENTS.voice_states = True

EXTENSIONS = ["src.cogs.voice", "src.cogs.settings", "src.cogs.phrases"]


class TTSBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=config.COMMAND_PREFIX,
            intents=INTENTS,
            help_command=None,
        )
        self.players = PlayerManager()
        self.last_said: dict[int, str] = {}
        self._synced = False

    async def setup_hook(self):
        await init_db()
        for extension in EXTENSIONS:
            await self.load_extension(extension)
        self.tree.on_error = self.on_app_command_error

    async def on_ready(self):
        if not self._synced:
            for guild in self.guilds:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            self._synced = True
        print(f"Logged in as {self.user} ({self.user.id})")

    async def on_guild_join(self, guild: discord.Guild):
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    # ── shared speech path ──────────────────────────────────────────────────────

    async def speak(
        self,
        member: discord.Member,
        text: str,
        *,
        speaker_name: str | None = None,
        already_clean: bool = False,
    ) -> bool:
        """Queue text to be spoken in the member's guild. False if not connected."""
        player = self.players.get(member.guild.id)
        if player is None:
            return False

        user_voice = await get_user_voice(member.id)
        guild_config = await get_guild_config(member.guild.id)
        replacements = await get_pronunciations(member.guild.id)

        voice = (
            (user_voice.voice if user_voice and user_voice.voice else None)
            or guild_config.default_voice
            or config.DEFAULT_VOICE
        )
        rate = user_voice.rate if user_voice else "+0%"
        pitch = user_voice.pitch if user_voice else "+0Hz"

        if not already_clean:
            text = normalize(text, replacements=replacements, max_chars=config.MAX_CHARS)
        if not text:
            return False

        if speaker_name and guild_config.say_names:
            text = f"{speaker_name} says: {text}"

        self.last_said[member.id] = text
        await player.enqueue(text, voice, rate, pitch)
        return True

    # ── errors ────────────────────────────────────────────────────────────────

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            message = "You need the Manage Server permission for that."
        elif isinstance(error, app_commands.CheckFailure):
            message = "You can't use that here."
        else:
            message = "Something went wrong."
            traceback.print_exception(type(error), error, error.__traceback__)

        embed = embeds.err(message)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
