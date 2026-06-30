import re

# ── patterns ────────────────────────────────────────────────────────────────

_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_SPOILER = re.compile(r"\|\|.*?\|\|", re.DOTALL)
_CUSTOM_EMOJI = re.compile(r"<a?:(\w+):\d+>")
_RAW_MENTION = re.compile(r"<(?:@[!&]?|#)\d+>")
_URL = re.compile(r"https?://\S+|www\.\S+")
_REPEAT = re.compile(r"(.)\1{3,}")
_MENTION_PREFIX = re.compile(r"[@#](?=\w)")
_MARKDOWN = re.compile(r"[*_~>`#]")
_WHITESPACE = re.compile(r"\s+")


def normalize(
    text: str,
    replacements: dict[str, str] | None = None,
    max_chars: int = 300,
) -> str:
    """Reduce a Discord message to clean, speakable text."""
    text = _CODE_BLOCK.sub(" code block ", text)
    text = _INLINE_CODE.sub(lambda m: m.group(1), text)
    text = _SPOILER.sub(" spoiler ", text)
    text = _CUSTOM_EMOJI.sub(lambda m: " " + m.group(1).replace("_", " ") + " ", text)
    text = _RAW_MENTION.sub(" ", text)  # safety net for unresolved mentions
    text = _URL.sub(" link ", text)
    text = _MENTION_PREFIX.sub("", text)  # drop @ / # left by resolved mentions
    text = _REPEAT.sub(lambda m: m.group(1) * 2, text)

    if replacements:
        for pattern, replacement in replacements.items():
            text = re.sub(
                rf"\b{re.escape(pattern)}\b",
                replacement,
                text,
                flags=re.IGNORECASE,
            )

    text = _MARKDOWN.sub("", text)
    text = _WHITESPACE.sub(" ", text).strip()

    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + " ..."

    return text
