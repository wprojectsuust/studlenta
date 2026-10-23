"""Команды обслуживания: создать модератора/админа, разослать напоминания (для cron)."""

import argparse
import asyncio
import getpass
import os
import sys
from pathlib import Path

import asyncpg

from studlenta.application.use_cases.send_favorite_reminders import SendFavoriteReminders
from studlenta.domain.users import Role, User, normalize_email, normalize_name, validate_password
from studlenta.infrastructure.db.uow import PostgresUnitOfWork
from studlenta.infrastructure.security import Argon2PasswordHasher
from studlenta.infrastructure.system import SystemClock, UuidGenerator


async def create_user_in_db(
    pool: asyncpg.Pool, email: str, full_name: str, role: Role, password: str
) -> User:
    validate_password(password)
    now = SystemClock().now()
    # Аккаунты из CLI создаёт администратор — почту считаем подтверждённой.
    user = User(UuidGenerator().new_id(), normalize_email(email), normalize_name(full_name), role,
                Argon2PasswordHasher().hash(password), now, email_verified_at=now)  # fmt: skip
    async with PostgresUnitOfWork(pool)() as uow:
        await uow.users.add(user)
        await uow.commit()
    return user


async def _with_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)


def create_user() -> None:  # pragma: no cover - интерактивная обёртка
    parser = argparse.ArgumentParser(description="Создать пользователя с ролью")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=[r.value for r in Role], default=Role.MODERATOR.value)
    args = parser.parse_args()
    password = os.environ.get("STUDLENTA_NEW_PASSWORD") or getpass.getpass("Пароль: ")

    async def run() -> None:
        pool = await _with_pool()
        try:
            user = await create_user_in_db(pool, args.email, args.name, Role(args.role), password)
            print(f"Создан {user.email} ({user.role})")
        finally:
            await pool.close()

    asyncio.run(run())


def rebuild_covers() -> None:  # pragma: no cover - разовая команда обслуживания
    from studlenta.infrastructure.files import PillowImageInspector
    from studlenta.infrastructure.files import rebuild_covers as rebuild
    from studlenta.infrastructure.settings import Settings

    settings = Settings()  # type: ignore[call-arg]
    print(f"Обновлено обложек: {rebuild(settings.media_root, PillowImageInspector())}")


def cleanup_media() -> None:  # pragma: no cover - запускается по расписанию
    from studlenta.infrastructure.files import cleanup_orphan_covers
    from studlenta.infrastructure.settings import Settings

    settings = Settings()  # type: ignore[call-arg]

    async def referenced() -> set[str]:
        pool = await _with_pool()
        try:
            rows = await pool.fetch("SELECT cover_url FROM events WHERE cover_url IS NOT NULL")
        finally:
            await pool.close()
        return {Path(r["cover_url"]).stem for r in rows}

    removed = cleanup_orphan_covers(settings.media_root, asyncio.run(referenced()))
    print(f"Удалено неиспользуемых обложек: {len(removed)}")


def send_reminders() -> None:  # pragma: no cover - запускается по расписанию
    async def run() -> int:
        pool = await _with_pool()
        try:
            return await SendFavoriteReminders(
                PostgresUnitOfWork(pool), SystemClock(), UuidGenerator()
            )()
        finally:
            await pool.close()

    print(f"Отправлено напоминаний: {asyncio.run(run())}")
    sys.exit(0)
