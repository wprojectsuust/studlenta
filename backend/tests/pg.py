"""Настоящий PostgreSQL для интеграционных и e2e-тестов.

По умолчанию поднимается контейнер через testcontainers. В CI можно передать готовую базу
через ``TEST_DATABASE_URL`` — тогда Docker не нужен.
"""

import os
from collections.abc import AsyncIterator, Iterator

import asyncpg
import pytest

from studlenta.infrastructure.db.migrate import apply_migrations

TABLES = (
    "users, events, likes, favorites, moderation_log, notifications, refresh_tokens, "
    "email_verifications, password_resets"
)


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    if url := os.environ.get("TEST_DATABASE_URL"):
        yield url
        return
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver=None) as pg:
        yield pg.get_connection_url()


@pytest.fixture(scope="session")
async def pool(database_url: str) -> AsyncIterator[asyncpg.Pool]:
    await apply_migrations(database_url)
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    yield pool
    await pool.close()


@pytest.fixture
async def clean_db(pool: asyncpg.Pool) -> None:
    await pool.execute(f"TRUNCATE {TABLES} CASCADE")
