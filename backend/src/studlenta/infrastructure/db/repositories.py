"""Репозитории записи на нативном SQL (asyncpg). Каждый работает в соединении транзакции UoW."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import asyncpg
from asyncpg.pool import PoolConnectionProxy

from studlenta.application.dto import (
    CategoryRef,
    CategoryWithCount,
    ModerationAction,
    ModerationLogEntry,
    Notification,
    NotificationKind,
    RefreshTokenRecord,
)
from studlenta.domain.categories import Category
from studlenta.domain.errors import ConflictError
from studlenta.domain.events import Event, EventContent, EventStatus
from studlenta.domain.users import Role, User

# Соединение из пула (прокси) или обычное — репозиториям всё равно.
type Conn = asyncpg.Connection[asyncpg.Record] | PoolConnectionProxy[asyncpg.Record]

_EVENT_COLUMNS = """
    id, author_id, category_id, title, summary, body, place, starts_at, ends_at, cover_url,
    status, moderator_note, created_at, updated_at, submitted_at, published_at, version
"""


def _event(r: asyncpg.Record) -> Event:
    return Event(
        id=r["id"],
        author_id=r["author_id"],
        content=EventContent(
            title=r["title"],
            summary=r["summary"],
            body=r["body"],
            category_id=r["category_id"],
            place=r["place"],
            starts_at=r["starts_at"],
            ends_at=r["ends_at"],
            cover_url=r["cover_url"],
        ),
        status=EventStatus(r["status"]),
        created_at=r["created_at"],
        updated_at=r["updated_at"],
        submitted_at=r["submitted_at"],
        published_at=r["published_at"],
        moderator_note=r["moderator_note"],
        version=r["version"],
    )


class PgEventRepository:
    def __init__(self, conn: Conn) -> None:
        self._conn = conn

    async def get(self, event_id: UUID) -> Event | None:
        row = await self._conn.fetchrow(
            f"SELECT {_EVENT_COLUMNS} FROM events WHERE id = $1", event_id
        )
        return _event(row) if row else None

    async def add(self, event: Event) -> None:
        c = event.content
        await self._conn.execute(
            f"INSERT INTO events ({_EVENT_COLUMNS}) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)",
            event.id, event.author_id, c.category_id, c.title, c.summary, c.body, c.place,
            c.starts_at, c.ends_at, c.cover_url, event.status.value, event.moderator_note,
            event.created_at, event.updated_at, event.submitted_at, event.published_at,
            event.version,
        )  # fmt: skip

    async def update(self, event: Event) -> None:
        c = event.content
        status = await self._conn.execute(
            """
            UPDATE events SET
                category_id = $3, title = $4, summary = $5, body = $6, place = $7,
                starts_at = $8, ends_at = $9, cover_url = $10, status = $11,
                moderator_note = $12, updated_at = $13, submitted_at = $14, published_at = $15,
                version = version + 1
            WHERE id = $1 AND version = $2
            """,
            event.id, event.version, c.category_id, c.title, c.summary, c.body, c.place,
            c.starts_at, c.ends_at, c.cover_url, event.status.value, event.moderator_note,
            event.updated_at, event.submitted_at, event.published_at,
        )  # fmt: skip
        if status != "UPDATE 1":
            raise ConflictError("Событие уже изменили — обновите страницу")
        event.version += 1

    async def delete(self, event_id: UUID) -> None:
        await self._conn.execute("DELETE FROM events WHERE id = $1", event_id)


def _user(r: asyncpg.Record) -> User:
    return User(
        r["id"], r["email"], r["full_name"], Role(r["role"]), r["password_hash"], r["created_at"]
    )


class PgUserRepository:
    def __init__(self, conn: Conn) -> None:
        self._conn = conn

    async def get(self, user_id: UUID) -> User | None:
        row = await self._conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        return _user(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        row = await self._conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
        return _user(row) if row else None

    async def add(self, user: User) -> None:
        try:
            async with self._conn.transaction():  # savepoint: ошибка не ломает всю транзакцию
                await self._conn.execute(
                    "INSERT INTO users (id, email, full_name, role, password_hash, created_at) "
                    "VALUES ($1, $2, $3, $4, $5, $6)",
                    user.id, user.email, user.full_name, user.role.value, user.password_hash,
                    user.created_at,
                )  # fmt: skip
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError("Почта уже зарегистрирована") from exc


def category_ref(r: asyncpg.Record, prefix: str = "") -> CategoryRef:
    p = prefix
    return CategoryRef(r[f"{p}id"], r[f"{p}slug"], r[f"{p}name"], r[f"{p}color"])


class PgCategoryRepository:
    def __init__(self, conn: Conn) -> None:
        self._conn = conn

    async def get(self, category_id: int) -> Category | None:
        row = await self._conn.fetchrow(
            "SELECT id, slug, name, color FROM categories WHERE id = $1", category_id
        )
        return Category(row["id"], row["slug"], row["name"], row["color"]) if row else None

    async def list_with_counts(self, upcoming_from: datetime) -> list[CategoryWithCount]:
        rows = await self._conn.fetch(
            """
            SELECT c.id, c.slug, c.name, c.color, count(e.id) AS upcoming
            FROM categories c
            LEFT JOIN events e
              ON e.category_id = c.id AND e.status = 'published' AND e.starts_at >= $1
            GROUP BY c.id
            ORDER BY c.position, c.id
            """,
            upcoming_from,
        )
        return [CategoryWithCount(category_ref(r), r["upcoming"]) for r in rows]


class PgReactionRepository:
    def __init__(self, conn: Conn) -> None:
        self._conn = conn

    async def _insert(self, table: str, user_id: UUID, event_id: UUID, now: datetime) -> None:
        await self._conn.execute(
            f"INSERT INTO {table} (user_id, event_id, created_at) VALUES ($1, $2, $3) "
            "ON CONFLICT DO NOTHING",
            user_id, event_id, now,
        )  # fmt: skip

    async def _delete(self, table: str, user_id: UUID, event_id: UUID) -> None:
        await self._conn.execute(
            f"DELETE FROM {table} WHERE user_id = $1 AND event_id = $2",
            user_id, event_id,
        )  # fmt: skip

    async def like(self, user_id: UUID, event_id: UUID, now: datetime) -> None:
        await self._insert("likes", user_id, event_id, now)

    async def unlike(self, user_id: UUID, event_id: UUID) -> None:
        await self._delete("likes", user_id, event_id)

    async def favorite(self, user_id: UUID, event_id: UUID, now: datetime) -> None:
        await self._insert("favorites", user_id, event_id, now)

    async def unfavorite(self, user_id: UUID, event_id: UUID) -> None:
        await self._delete("favorites", user_id, event_id)

    async def published_ids(self, event_ids: Sequence[UUID]) -> set[UUID]:
        rows = await self._conn.fetch(
            "SELECT id FROM events WHERE id = ANY($1::uuid[]) AND status = 'published'",
            list(event_ids),
        )
        return {r["id"] for r in rows}

    async def favorites_starting_between(
        self, start: datetime, end: datetime
    ) -> list[tuple[UUID, UUID, str]]:
        rows = await self._conn.fetch(
            """
            SELECT f.user_id, e.id, e.title
            FROM favorites f JOIN events e ON e.id = f.event_id
            WHERE e.status = 'published' AND e.starts_at >= $1 AND e.starts_at < $2
            ORDER BY f.user_id, e.starts_at, e.id
            """,
            start, end,
        )  # fmt: skip
        return [(r["user_id"], r["id"], r["title"]) for r in rows]


class PgModerationLogRepository:
    def __init__(self, conn: Conn) -> None:
        self._conn = conn

    async def add(self, entry: ModerationLogEntry) -> None:
        await self._conn.execute(
            "INSERT INTO moderation_log (event_id, actor_id, action, note, created_at) "
            "VALUES ($1, $2, $3, $4, $5)",
            entry.event_id, entry.actor_id, entry.action.value, entry.note, entry.created_at,
        )  # fmt: skip

    async def list_for_event(self, event_id: UUID) -> list[ModerationLogEntry]:
        rows = await self._conn.fetch(
            """
            SELECT m.event_id, m.actor_id, m.action, m.note, m.created_at, u.full_name
            FROM moderation_log m JOIN users u ON u.id = m.actor_id
            WHERE m.event_id = $1
            ORDER BY m.created_at DESC, m.id DESC
            """,
            event_id,
        )
        return [
            ModerationLogEntry(r["event_id"], r["actor_id"], ModerationAction(r["action"]),
                               r["note"], r["created_at"], r["full_name"])
            for r in rows
        ]  # fmt: skip


class PgNotificationRepository:
    def __init__(self, conn: Conn) -> None:
        self._conn = conn

    async def add(self, n: Notification) -> bool:
        status = await self._conn.execute(
            "INSERT INTO notifications (id, user_id, kind, event_id, text, created_at, read_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT DO NOTHING",
            n.id, n.user_id, n.kind.value, n.event_id, n.text, n.created_at, n.read_at,
        )  # fmt: skip
        return bool(status == "INSERT 0 1")

    async def list_for_user(
        self, user_id: UUID, limit: int, before: datetime | None
    ) -> list[Notification]:
        rows = await self._conn.fetch(
            """
            SELECT * FROM notifications
            WHERE user_id = $1 AND ($3::timestamptz IS NULL OR created_at < $3)
            ORDER BY created_at DESC, id
            LIMIT $2
            """,
            user_id, limit, before,
        )  # fmt: skip
        return [
            Notification(r["id"], r["user_id"], NotificationKind(r["kind"]), r["event_id"],
                         r["text"], r["created_at"], r["read_at"])
            for r in rows
        ]  # fmt: skip

    async def count_unread(self, user_id: UUID) -> int:
        value = await self._conn.fetchval(
            "SELECT count(*) FROM notifications WHERE user_id = $1 AND read_at IS NULL", user_id
        )
        return int(value)

    async def mark_read(self, user_id: UUID, ids: Sequence[UUID] | None, now: datetime) -> None:
        await self._conn.execute(
            """
            UPDATE notifications SET read_at = $3
            WHERE user_id = $1 AND read_at IS NULL AND ($2::uuid[] IS NULL OR id = ANY($2))
            """,
            user_id, list(ids) if ids is not None else None, now,
        )  # fmt: skip


class PgRefreshTokenRepository:
    def __init__(self, conn: Conn) -> None:
        self._conn = conn

    async def add(self, record: RefreshTokenRecord) -> None:
        await self._conn.execute(
            "INSERT INTO refresh_tokens (token_hash, user_id, expires_at, revoked_at) "
            "VALUES ($1, $2, $3, $4)",
            record.token_hash, record.user_id, record.expires_at, record.revoked_at,
        )  # fmt: skip

    async def get(self, token_hash: str) -> RefreshTokenRecord | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM refresh_tokens WHERE token_hash = $1", token_hash
        )
        if row is None:
            return None
        return RefreshTokenRecord(row["token_hash"], row["user_id"], row["expires_at"],
                                  row["revoked_at"])  # fmt: skip

    async def revoke(self, token_hash: str, now: datetime) -> None:
        await self._conn.execute(
            "UPDATE refresh_tokens SET revoked_at = $2 "
            "WHERE token_hash = $1 AND revoked_at IS NULL",
            token_hash, now,
        )  # fmt: skip
