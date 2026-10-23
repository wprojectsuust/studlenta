"""Минимальный раннер миграций: SQL-файлы ``NNNN_name.sql`` применяются по порядку, по одному
в транзакции, и записываются в ``schema_migrations``. Advisory lock защищает от двух
одновременных запусков (например, при старте нескольких реплик).
"""

import asyncio
import os
from importlib import resources

import asyncpg

LOCK_ID = 2026_10_23
_CREATE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
)
"""


def _migrations() -> list[tuple[str, str]]:
    folder = resources.files("studlenta.infrastructure.db") / "migrations"
    files = sorted((f for f in folder.iterdir() if f.name.endswith(".sql")), key=lambda f: f.name)
    return [(f.name.removesuffix(".sql"), f.read_text(encoding="utf-8")) for f in files]


async def apply_migrations(dsn: str) -> list[str]:
    """Применяет недостающие миграции и возвращает их версии."""
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute("SELECT pg_advisory_lock($1)", LOCK_ID)
        try:
            await conn.execute(_CREATE)
            done = {r["version"] for r in await conn.fetch("SELECT version FROM schema_migrations")}
            applied = []
            for version, sql in _migrations():
                if version in done:
                    continue
                async with conn.transaction():
                    await conn.execute(sql)
                    await conn.execute(
                        "INSERT INTO schema_migrations (version) VALUES ($1)", version
                    )
                applied.append(version)
            return applied
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", LOCK_ID)
    finally:
        await conn.close()


def main() -> None:  # pragma: no cover - тонкая обёртка для CLI
    applied = asyncio.run(apply_migrations(os.environ["DATABASE_URL"]))
    print("Применено:", ", ".join(applied) if applied else "ничего, база актуальна")
