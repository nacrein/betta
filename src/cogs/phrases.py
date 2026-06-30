import discord
from discord import app_commands
from discord.ext import commands

from .. import embeds
from ..db import add_phrase, list_phrases, remove_phrase


class PhraseButton(discord.ui.Button):
    def __init__(self, label: str, text: str, owner_id: int):
        super().__init__(label=label[:80], style=discord.ButtonStyle.secondary)
        self.text = text
        self.owner_id = owner_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                embed=embeds.err("This board isn't yours."), ephemeral=True
            )
            return
        spoke = await interaction.client.speak(interaction.user, self.text)
        if spoke:
            await interaction.response.send_message(
                f"{embeds.Emojis.SPEAK} {self.text}", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=embeds.err("I'm not in a voice channel. Use /join."),
                ephemeral=True,
            )


class Soundboard(discord.ui.View):
    def __init__(self, owner_id: int, phrases: list[tuple[str, str]]):
        super().__init__(timeout=None)
        for label, text in phrases[:25]:
            self.add_item(PhraseButton(label, text, owner_id))


class Phrases(commands.Cog):
    phrase = app_commands.Group(
        name="phrase", description="Your saved quick phrases."
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @phrase.command(name="add", description="Save a quick phrase.")
    @app_commands.guild_only()
    @app_commands.describe(label="Short button name", text="What it should say")
    async def phrase_add(
        self, interaction: discord.Interaction, label: str, text: str
    ):
        await add_phrase(interaction.guild.id, interaction.user.id, label, text[:300])
        await interaction.response.send_message(
            embed=embeds.ok(f"Saved **{label}**."), ephemeral=True
        )

    @phrase.command(name="remove", description="Delete a quick phrase.")
    @app_commands.guild_only()
    async def phrase_remove(self, interaction: discord.Interaction, label: str):
        removed = await remove_phrase(
            interaction.guild.id, interaction.user.id, label
        )
        message = f"Removed **{label}**." if removed else f"**{label}** was not found."
        await interaction.response.send_message(
            embed=embeds.ok(message), ephemeral=True
        )

    @app_commands.command(description="Open your quick-phrase soundboard.")
    @app_commands.guild_only()
    async def board(self, interaction: discord.Interaction):
        phrases = await list_phrases(interaction.guild.id, interaction.user.id)
        if not phrases:
            await interaction.response.send_message(
                embed=embeds.info("No phrases yet. Add some with /phrase add."),
                ephemeral=True,
            )
            return
        view = Soundboard(interaction.user.id, phrases)
        await interaction.response.send_message(
            embed=embeds.info(
                "Tap a phrase to speak it.", title=f"{embeds.Emojis.SPEAK} Soundboard"
            ),
            view=view,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Phrases(bot))
