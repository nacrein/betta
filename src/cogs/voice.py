import discord
from discord import app_commands
from discord.ext import commands

from .. import embeds
from ..db import get_guild_config, is_blocked, get_user_voice


def resolve_mentions(message: discord.Message) -> str:
    """Replace raw mention tokens with readable names (Discord-layer work)."""
    content = message.content
    for user in message.mentions:
        name = user.display_name
        content = content.replace(f"<@{user.id}>", name).replace(
            f"<@!{user.id}>", name
        )
    for role in message.role_mentions:
        content = content.replace(f"<@&{role.id}>", role.name)
    for channel in message.channel_mentions:
        content = content.replace(f"<#{channel.id}>", channel.name)
    return content


class Voice(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── commands ────────────────────────────────────────────────────────────

    @app_commands.command(description="Join your current voice channel.")
    @app_commands.guild_only()
    async def join(self, interaction: discord.Interaction):
        voice_state = interaction.user.voice
        if voice_state is None or voice_state.channel is None:
            await interaction.response.send_message(
                embed=embeds.err("Join a voice channel first, then run /join."),
                ephemeral=True,
            )
            return

        channel = voice_state.channel
        existing = interaction.guild.voice_client
        if existing is not None:
            await existing.move_to(channel)
        else:
            vc = await channel.connect()
            self.bot.players.create(vc)
        await interaction.response.send_message(
            embed=embeds.ok(f"Joined **{channel.name}**.")
        )

    @app_commands.command(description="Leave the voice channel.")
    @app_commands.guild_only()
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client is None:
            await interaction.response.send_message(
                embed=embeds.err("I'm not in a voice channel."), ephemeral=True
            )
            return
        await self.bot.players.destroy(interaction.guild.id)
        await interaction.response.send_message(embed=embeds.ok("Left the channel."))

    @app_commands.command(description="Skip the message being read.")
    @app_commands.guild_only()
    async def skip(self, interaction: discord.Interaction):
        player = self.bot.players.get(interaction.guild.id)
        if player is None:
            await interaction.response.send_message(
                embed=embeds.err("I'm not in a voice channel."), ephemeral=True
            )
            return
        player.skip()
        await interaction.response.send_message(
            embed=embeds.ok("Skipped."), ephemeral=True
        )

    @app_commands.command(description="Clear everything queued to be read.")
    @app_commands.guild_only()
    async def clear(self, interaction: discord.Interaction):
        player = self.bot.players.get(interaction.guild.id)
        if player is None:
            await interaction.response.send_message(
                embed=embeds.err("I'm not in a voice channel."), ephemeral=True
            )
            return
        player.clear()
        await interaction.response.send_message(
            embed=embeds.ok("Queue cleared."), ephemeral=True
        )

    @app_commands.command(description="Speak a line in your voice.")
    @app_commands.guild_only()
    async def say(self, interaction: discord.Interaction, text: str):
        spoke = await self.bot.speak(interaction.user, text)
        if spoke:
            await interaction.response.send_message(
                embed=embeds.ok("Queued."), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=embeds.err("I'm not in a voice channel. Use /join."),
                ephemeral=True,
            )

    @app_commands.command(description="Say your last line again.")
    @app_commands.guild_only()
    async def again(self, interaction: discord.Interaction):
        last = self.bot.last_said.get(interaction.user.id)
        if not last:
            await interaction.response.send_message(
                embed=embeds.err("Nothing to repeat yet."), ephemeral=True
            )
            return
        spoke = await self.bot.speak(interaction.user, last, already_clean=True)
        if spoke:
            await interaction.response.send_message(
                embed=embeds.ok("Repeated."), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=embeds.err("I'm not in a voice channel. Use /join."),
                ephemeral=True,
            )

    # ── listeners ────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        if not message.content:
            return
        if message.content.startswith(self.bot.command_prefix):
            return

        config = await get_guild_config(message.guild.id)
        if config.tts_channel_id is None:
            return
        if message.channel.id != config.tts_channel_id:
            return

        user_voice = await get_user_voice(message.author.id)
        if user_voice and user_voice.opted_out:
            return
        if await is_blocked(message.guild.id, message.author.id):
            return

        body = resolve_mentions(message)
        await self.bot.speak(
            message.author, body, speaker_name=message.author.display_name
        )

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        guild = member.guild
        vc = guild.voice_client

        # Auto-leave: if my channel has no humans left, disconnect.
        if vc is not None and vc.channel is not None:
            if not any(not m.bot for m in vc.channel.members):
                await self.bot.players.destroy(guild.id)
                return

        if member.bot:
            return

        # Auto-join: if enabled and a human joined while I'm idle, follow them.
        if after.channel is not None and vc is None:
            config = await get_guild_config(guild.id)
            if config.auto_join:
                try:
                    new_vc = await after.channel.connect()
                except discord.ClientException:
                    return
                self.bot.players.create(new_vc)


async def setup(bot: commands.Bot):
    await bot.add_cog(Voice(bot))
