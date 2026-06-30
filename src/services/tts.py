import asyncio
import contextlib
import os
import tempfile

import edge_tts
from gtts import gTTS


class TTSError(Exception):
    pass


async def synthesize(
    text: str,
    voice: str,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> str:
    """Synthesize speech to a temp mp3 and return its path.

    Tries edge-tts first (neural, free). If that fails for any reason
    (network, rate limit, the periodic 403), it falls back to gTTS so the
    user is never left without a voice mid-conversation. The caller owns
    the returned file and must delete it.
    """
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)

    try:
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(path)
        if os.path.getsize(path) > 0:
            return path
        raise RuntimeError("edge-tts returned empty audio")
    except Exception:
        with contextlib.suppress(Exception):
            lang = voice.split("-")[0] if voice else "en"
            await asyncio.to_thread(_gtts_save, text, lang, path)
            if os.path.getsize(path) > 0:
                return path
        with contextlib.suppress(OSError):
            os.remove(path)
        raise TTSError("all TTS engines failed")


def _gtts_save(text: str, lang: str, path: str) -> None:
    gTTS(text=text, lang=lang).save(path)
