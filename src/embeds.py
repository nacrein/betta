import discord


class Emojis:
    OK = "\u2705"      # ✅
    ERR = "\u26a0\ufe0f"  # ⚠️
    SPEAK = "\U0001f5e3\ufe0f"  # 🗣️
    MUTE = "\U0001f507"  # 🔇


# ── builders ────────────────────────────────────────────────────────────────

def ok(description: str, title: str | None = None) -> discord.Embed:
    embed = discord.Embed(description=f"{Emojis.OK} {description}", color=0x57F287)
    if title:
        embed.title = title
    return embed


def err(description: str) -> discord.Embed:
    return discord.Embed(description=f"{Emojis.ERR} {description}", color=0xED4245)


def info(description: str, title: str | None = None) -> discord.Embed:
    embed = discord.Embed(description=description, color=0x5865F2)
    if title:
        embed.title = title
    return embed
