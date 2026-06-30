import contextlib
import os
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
    String,
    UniqueConstraint,
    delete,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from . import config


class Base(DeclarativeBase):
    pass


# ── models ────────────────────────────────────────────────────────────────

class UserVoice(Base):
    __tablename__ = "user_voice"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    voice: Mapped[Optional[str]] = mapped_column(String(64))
    rate: Mapped[str] = mapped_column(String(8), default="+0%")
    pitch: Mapped[str] = mapped_column(String(8), default="+0Hz")
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)


class GuildConfig(Base):
    __tablename__ = "guild_config"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tts_channel_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    say_names: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_join: Mapped[bool] = mapped_column(Boolean, default=False)
    default_voice: Mapped[Optional[str]] = mapped_column(String(64))


class Pronunciation(Base):
    __tablename__ = "pronunciation"
    __table_args__ = (UniqueConstraint("guild_id", "pattern", name="uq_pron"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    pattern: Mapped[str] = mapped_column(String(100))
    replacement: Mapped[str] = mapped_column(String(100))


class Phrase(Base):
    __tablename__ = "phrase"
    __table_args__ = (
        UniqueConstraint("guild_id", "owner_id", "label", name="uq_phrase"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, index=True)
    label: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(String(300))


class Blocklist(Base):
    __tablename__ = "blocklist"
    __table_args__ = (UniqueConstraint("guild_id", "user_id", name="uq_block"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)


# ── return types ────────────────────────────────────────────────────────────

@dataclass
class VoiceSettings:
    voice: Optional[str]
    rate: str
    pitch: str
    opted_out: bool


@dataclass
class GuildSettings:
    tts_channel_id: Optional[int]
    say_names: bool
    auto_join: bool
    default_voice: Optional[str]


# ── engine ────────────────────────────────────────────────────────────────

engine = create_async_engine(config.DATABASE_URL)
Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    if config.DATABASE_URL.startswith("sqlite"):
        path = config.DATABASE_URL.split("///", 1)[-1]
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _get_or_create_guild(session: AsyncSession, guild_id: int) -> GuildConfig:
    row = await session.get(GuildConfig, guild_id)
    if row is None:
        row = GuildConfig(guild_id=guild_id)
        session.add(row)
    return row


# ── user voices ─────────────────────────────────────────────────────────────

async def get_user_voice(user_id: int) -> Optional[VoiceSettings]:
    async with Session() as session:
        row = await session.get(UserVoice, user_id)
        if row is None:
            return None
        return VoiceSettings(row.voice, row.rate, row.pitch, row.opted_out)


async def set_user_voice(
    user_id: int,
    *,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    pitch: Optional[str] = None,
) -> None:
    async with Session() as session:
        row = await session.get(UserVoice, user_id)
        if row is None:
            row = UserVoice(user_id=user_id)
            session.add(row)
        if voice is not None:
            row.voice = voice
        if rate is not None:
            row.rate = rate
        if pitch is not None:
            row.pitch = pitch
        await session.commit()


async def set_opt_out(user_id: int, value: bool) -> None:
    async with Session() as session:
        row = await session.get(UserVoice, user_id)
        if row is None:
            row = UserVoice(user_id=user_id)
            session.add(row)
        row.opted_out = value
        await session.commit()


# ── guild config ────────────────────────────────────────────────────────────

async def get_guild_config(guild_id: int) -> GuildSettings:
    async with Session() as session:
        row = await session.get(GuildConfig, guild_id)
        if row is None:
            return GuildSettings(None, False, False, None)
        return GuildSettings(
            row.tts_channel_id, row.say_names, row.auto_join, row.default_voice
        )


async def set_tts_channel(guild_id: int, channel_id: Optional[int]) -> None:
    async with Session() as session:
        row = await _get_or_create_guild(session, guild_id)
        row.tts_channel_id = channel_id
        await session.commit()


async def set_say_names(guild_id: int, value: bool) -> None:
    async with Session() as session:
        row = await _get_or_create_guild(session, guild_id)
        row.say_names = value
        await session.commit()


async def set_auto_join(guild_id: int, value: bool) -> None:
    async with Session() as session:
        row = await _get_or_create_guild(session, guild_id)
        row.auto_join = value
        await session.commit()


async def set_default_voice(guild_id: int, voice: str) -> None:
    async with Session() as session:
        row = await _get_or_create_guild(session, guild_id)
        row.default_voice = voice
        await session.commit()


# ── pronunciation ─────────────────────────────────────────────────────────

async def add_pronunciation(guild_id: int, pattern: str, replacement: str) -> None:
    async with Session() as session:
        existing = await session.scalar(
            select(Pronunciation).where(
                Pronunciation.guild_id == guild_id,
                Pronunciation.pattern == pattern,
            )
        )
        if existing:
            existing.replacement = replacement
        else:
            session.add(
                Pronunciation(
                    guild_id=guild_id, pattern=pattern, replacement=replacement
                )
            )
        await session.commit()


async def remove_pronunciation(guild_id: int, pattern: str) -> bool:
    async with Session() as session:
        result = await session.execute(
            delete(Pronunciation).where(
                Pronunciation.guild_id == guild_id,
                Pronunciation.pattern == pattern,
            )
        )
        await session.commit()
        return result.rowcount > 0


async def list_pronunciations(guild_id: int) -> list[tuple[str, str]]:
    async with Session() as session:
        rows = (
            await session.scalars(
                select(Pronunciation)
                .where(Pronunciation.guild_id == guild_id)
                .order_by(Pronunciation.pattern)
            )
        ).all()
        return [(row.pattern, row.replacement) for row in rows]


async def get_pronunciations(guild_id: int) -> dict[str, str]:
    return dict(await list_pronunciations(guild_id))


# ── phrases ────────────────────────────────────────────────────────────────

async def add_phrase(guild_id: int, owner_id: int, label: str, text: str) -> None:
    async with Session() as session:
        existing = await session.scalar(
            select(Phrase).where(
                Phrase.guild_id == guild_id,
                Phrase.owner_id == owner_id,
                Phrase.label == label,
            )
        )
        if existing:
            existing.text = text
        else:
            session.add(
                Phrase(
                    guild_id=guild_id, owner_id=owner_id, label=label, text=text
                )
            )
        await session.commit()


async def remove_phrase(guild_id: int, owner_id: int, label: str) -> bool:
    async with Session() as session:
        result = await session.execute(
            delete(Phrase).where(
                Phrase.guild_id == guild_id,
                Phrase.owner_id == owner_id,
                Phrase.label == label,
            )
        )
        await session.commit()
        return result.rowcount > 0


async def list_phrases(guild_id: int, owner_id: int) -> list[tuple[str, str]]:
    async with Session() as session:
        rows = (
            await session.scalars(
                select(Phrase)
                .where(Phrase.guild_id == guild_id, Phrase.owner_id == owner_id)
                .order_by(Phrase.label)
            )
        ).all()
        return [(row.label, row.text) for row in rows]


# ── blocklist ────────────────────────────────────────────────────────────

async def block_user(guild_id: int, user_id: int) -> None:
    async with Session() as session:
        existing = await session.scalar(
            select(Blocklist).where(
                Blocklist.guild_id == guild_id, Blocklist.user_id == user_id
            )
        )
        if existing is None:
            session.add(Blocklist(guild_id=guild_id, user_id=user_id))
            await session.commit()


async def unblock_user(guild_id: int, user_id: int) -> bool:
    async with Session() as session:
        result = await session.execute(
            delete(Blocklist).where(
                Blocklist.guild_id == guild_id, Blocklist.user_id == user_id
            )
        )
        await session.commit()
        return result.rowcount > 0


async def is_blocked(guild_id: int, user_id: int) -> bool:
    async with Session() as session:
        row = await session.scalar(
            select(Blocklist).where(
                Blocklist.guild_id == guild_id, Blocklist.user_id == user_id
            )
        )
        return row is not None
