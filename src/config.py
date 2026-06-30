import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional; real env vars work fine
    pass

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or "0")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
MAX_CHARS = int(os.getenv("MAX_CHARS", "300"))
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "en-US-AriaNeural")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/tts.sqlite3")

# Fallback shown by /voice list when the live voice catalogue is unreachable
# (the edge endpoint can rate-limit or 403, same as the synthesis endpoint).
COMMON_VOICES = [
    "en-US-AriaNeural", "en-US-JennyNeural", "en-US-GuyNeural", "en-US-AnaNeural",
    "en-US-ChristopherNeural", "en-US-MichelleNeural", "en-GB-SoniaNeural",
    "en-GB-RyanNeural", "en-GB-LibbyNeural", "en-AU-NatashaNeural",
    "en-AU-WilliamNeural", "en-CA-ClaraNeural", "en-CA-LiamNeural",
    "en-IE-EmilyNeural", "en-IN-NeerjaNeural", "en-IN-PrabhatNeural",
]


def require_token() -> None:
    if not TOKEN:
        raise SystemExit(
            "DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in."
        )
