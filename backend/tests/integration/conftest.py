from datetime import timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest

from studlenta.domain.events import Event, EventContent
from studlenta.domain.users import Role, User
from studlenta.infrastructure.db.uow import PostgresUnitOfWork
from tests.fakes import NOW
from tests.pg import clean_db, database_url, pool

__all__ = ["clean_db", "database_url", "pool"]


@pytest.fixture(autouse=True)
async def clean(clean_db: None) -> None:
    return clean_db


@pytest.fixture
def uow(pool: asyncpg.Pool) -> PostgresUnitOfWork:
    """Фабрика: каждый ``uow()`` — отдельная транзакция, как в приложении."""
    return PostgresUnitOfWork(pool)


async def make_user(pool: asyncpg.Pool, role: Role = Role.AUTHOR, name: str = "Анна") -> User:
    user = User(uuid4(), f"{uuid4().hex[:8]}@uust.ru", name, role, "hash", NOW)
    async with PostgresUnitOfWork(pool)() as uow:
        await uow.users.add(user)
        await uow.commit()
    return user


async def category_id(pool: asyncpg.Pool, slug: str) -> int:
    value = await pool.fetchval("SELECT id FROM categories WHERE slug = $1", slug)
    assert isinstance(value, int)
    return value


async def make_event(
    pool: asyncpg.Pool,
    author: User,
    *,
    status: str = "published",
    title: str = "Вечер студенческой музыки",
    summary: str = "Живой звук и любимые хиты",
    category: str = "concerts",
    starts_in: timedelta = timedelta(days=2),
    event_id: UUID | None = None,
) -> Event:
    content = EventContent(
        title=title,
        summary=summary,
        body="Подробное описание события для студентов университета.",
        category_id=await category_id(pool, category),
        place="Актовый зал УУНиТ",
        starts_at=NOW + starts_in,
    )
    # Отправляем «из прошлого», чтобы можно было создавать и уже прошедшие события.
    event = Event.create_draft(
        event_id=event_id or uuid4(),
        author_id=author.id,
        content=content,
        now=NOW - timedelta(days=365),
    )
    if status != "draft":
        event.submit(now=NOW - timedelta(days=365))
    if status == "published":
        event.approve(now=NOW - timedelta(days=1))
    elif status == "changes_requested":
        event.request_changes(note="Поправьте", now=NOW)
    elif status == "rejected":
        event.reject(note="Реклама", now=NOW)
    elif status == "archived":
        event.approve(now=NOW)
        event.archive(now=NOW)
    async with PostgresUnitOfWork(pool)() as uow:
        await uow.events.add(event)
        await uow.commit()
    return event
