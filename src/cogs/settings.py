import discord
import edge_tts
from discord import app_commands
from discord.ext import commands

from .. import config, embeds
from ..db import (
    add_pronunciation,
    block_user,
    get_user_voice,
    list_pronunciations,
    remove_pronunciation,
    set_auto_join,
    set_default_voice,
    set_opt_out,
    set_say_names,
    set_tts_channel,
    set_user_voice,
    unblock_user,
)


class Settings(commands.Cog):
    voice = app_commands.Group(name="voice", description="Your text-to-speech voice.")
    setup = app_commands.Group(
        name="setup", description="Server text-to-speech settings."
    )
    dictionary = app_commands.Group(
        name="dict", description="How the bot pronounces words."
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._voice_cache: list[str] | None = None

    async def _voices(self) -> list[str]:
        if self._voice_cache is None:
            try:
                catalogue = await edge_tts.list_voices()
                self._voice_cache = sorted(v["ShortName"] for v in catalogue)
            except Exception:
                self._voice_cache = list(config.COMMON_VOICES)
        return self._voice_cache

    # ── voice (per user) ──────────────────────────────────────────────────────

    @voice.command(name="set", description="Set your voice, speed, and pitch.")
    @app_commands.guild_only()
    @app_commands.describe(
        voice="A voice name like en-US-AriaNeural (see /voice list)",
        rate="Speed, e.g. +0%, -20%, +25%",
        pitch="Pitch, e.g. +0Hz, -10Hz, +15Hz",
    )
    async def voice_set(
        self,
        interaction: discord.Interaction,
        voice: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ):
        await set_user_voice(interaction.user.id, voice=voice, rate=rate, pitch=pitch)
        note = "" if "Neural" in voice else " (that name looks unusual, double-check /voice list)"
        await interaction.response.send_message(
            embed=embeds.ok(f"Your voice is now **{voice}** at rate {rate}, pitch {pitch}.{note}"),
            ephemeral=True,
        )

    @voice.command(name="show", description="Show your current voice settings.")
    @app_commands.guild_only()
    async def voice_show(self, interaction: discord.Interaction):
        settings = await get_user_voice(interaction.user.id)
        voice = settings.voice if settings and settings.voice else config.DEFAULT_VOICE
        rate = settings.rate if settings else "+0%"
        pitch = settings.pitch if settings else "+0Hz"
        await interaction.response.send_message(
            embed=embeds.info(f"Voice **{voice}**, rate {rate}, pitch {pitch}."),
            ephemeral=True,
        )

    @voice.command(name="list", description="List available voices.")
    @app_commands.guild_only()
    @app_commands.describe(search="Filter by language or name, e.g. en-GB or Aria")
    async def voice_list(
        self, interaction: discord.Interaction, search: str | None = None
    ):
        await interaction.response.defer(ephemeral=True)
        voices = await self._voices()
        if search:
            needle = search.lower()
            voices = [v for v in voices if needle in v.lower()]
        if not voices:
            await interaction.followup.send(
                embed=embeds.err("No voices matched that search."), ephemeral=True
            )
            return
        shown = voices[:25]
        body = "\n".join(shown)
        if len(voices) > len(shown):
            body += f"\n\n...and {len(voices) - len(shown)} more. Narrow it with a search."
        await interaction.followup.send(
            embed=embeds.info(body, title="Voices"), ephemeral=True
        )

    # ── opt out / in ──────────────────────────────────────────────────────────

    @app_commands.command(description="Stop the bot reading your messages.")
    @app_commands.guild_only()
    async def optout(self, interaction: discord.Interaction):
        await set_opt_out(interaction.user.id, True)
        await interaction.response.send_message(
            embed=embeds.ok("I'll stop reading your messages."), ephemeral=True
        )

    @app_commands.command(description="Let the bot read your messages again.")
    @app_commands.guild_only()
    async def optin(self, interaction: discord.Interaction):
        await set_opt_out(interaction.user.id, False)
        await interaction.response.send_message(
            embed=embeds.ok("I'll read your messages again."), ephemeral=True
        )

    # ── setup (admin) ──────────────────────────────────────────────────────────

    @setup.command(name="channel", description="Set the channel that gets read aloud.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        await set_tts_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(
            embed=embeds.ok(f"Now reading messages from {channel.mention}.")
        )

    @setup.command(name="names", description="Read the speaker's name before each message.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_names(self, interaction: discord.Interaction, enabled: bool):
        await set_say_names(interaction.guild.id, enabled)
        state = "on" if enabled else "off"
        await interaction.response.send_message(
            embed=embeds.ok(f"Speaker names turned {state}.")
        )

    @setup.command(name="autojoin", description="Join a voice channel when someone enters it.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_autojoin(self, interaction: discord.Interaction, enabled: bool):
        await set_auto_join(interaction.guild.id, enabled)
        state = "on" if enabled else "off"
        await interaction.response.send_message(
            embed=embeds.ok(f"Auto-join turned {state}.")
        )

    @setup.command(name="defaultvoice", description="Set the server's fallback voice.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_defaultvoice(self, interaction: discord.Interaction, voice: str):
        await set_default_voice(interaction.guild.id, voice)
        await interaction.response.send_message(
            embed=embeds.ok(f"Default voice set to **{voice}**.")
        )

    # ── blocklist (admin) ──────────────────────────────────────────────────────

    @app_commands.command(description="Stop the bot reading a member.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def block(self, interaction: discord.Interaction, member: discord.Member):
        await block_user(interaction.guild.id, member.id)
        await interaction.response.send_message(
            embed=embeds.ok(f"{member.display_name} is blocked from TTS.")
        )

    @app_commands.command(description="Let the bot read a member again.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def unblock(self, interaction: discord.Interaction, member: discord.Member):
        removed = await unblock_user(interaction.guild.id, member.id)
        message = (
            f"{member.display_name} is unblocked."
            if removed
            else f"{member.display_name} was not blocked."
        )
        await interaction.response.send_message(embed=embeds.ok(message))

    # ── dictionary (admin) ──────────────────────────────────────────────────────

    @dictionary.command(name="add", description="Teach the bot how to say a word.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(word="The written word", say_as="How it should sound")
    async def dict_add(
        self, interaction: discord.Interaction, word: str, say_as: str
    ):
        await add_pronunciation(interaction.guild.id, word, say_as)
        await interaction.response.send_message(
            embed=embeds.ok(f"**{word}** will be read as **{say_as}**.")
        )

    @dictionary.command(name="remove", description="Forget a pronunciation.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def dict_remove(self, interaction: discord.Interaction, word: str):
        removed = await remove_pronunciation(interaction.guild.id, word)
        message = f"Removed **{word}**." if removed else f"**{word}** was not in the dictionary."
        await interaction.response.send_message(embed=embeds.ok(message))

    @dictionary.command(name="list", description="Show the pronunciation dictionary.")
    @app_commands.guild_only()
    async def dict_list(self, interaction: discord.Interaction):
        entries = await list_pronunciations(interaction.guild.id)
        if not entries:
            await interaction.response.send_message(
                embed=embeds.info("The dictionary is empty."), ephemeral=True
            )
            return
        body = "\n".join(f"{word} -> {say_as}" for word, say_as in entries)
        await interaction.response.send_message(
            embed=embeds.info(body, title="Pronunciation"), ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))
