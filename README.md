# TTS Bot

A focused Discord text-to-speech bot. Someone types in a designated channel
and the bot speaks it in their voice. Built for accessibility: persistent
per-person voices, a quick-phrase soundboard, and an engine fallback so a
single outage never leaves anyone without a voice.

## Requirements

- Python 3.11+ (discord.py 2.7+ for the mandatory voice E2EE support)
- FFmpeg installed and on PATH
- A bot application in the Discord Developer Portal with these **privileged
  intents** enabled: Message Content and Server Members

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env          # then paste your token in
python -m src
```

## Run with Docker

```bash
cp .env.example .env          # paste your token in
docker compose up -d --build
```

To host it alongside another bot, drop the `tts-bot` service from
`docker-compose.yml` into that project's compose file and bring the box up
together.

## Commands

- `/join`, `/leave` — connect to or leave your voice channel
- `/say <text>`, `/again` — speak a line, or repeat your last one
- `/skip`, `/clear` — skip the current message or empty the queue
- `/voice set|show|list` — pick your voice, speed, and pitch
- `/optout`, `/optin` — control whether your messages are read
- `/phrase add|remove`, `/board` — manage and open your quick-phrase soundboard
- `/setup channel|names|autojoin|defaultvoice` — server settings (Manage Server)
- `/dict add|remove|list` — pronunciation dictionary (Manage Server)
- `/block`, `/unblock` — mute a member from TTS (Manage Server)

## Setup flow

1. Invite the bot, then run `/setup channel #your-channel`.
2. Join a voice channel and run `/join`.
3. Type in the channel. It speaks.

## Notes

- Voices come from edge-tts (free, neural). If that endpoint is unreachable,
  synthesis falls back to gTTS automatically.
- Audio is generated per message with no cache; adding one keyed on
  (voice, params, text) is the obvious next optimization if latency matters.
- Soundboard buttons work until the bot restarts; rerun `/board` after a
  restart, or wire persistent views if you want them to survive one.
