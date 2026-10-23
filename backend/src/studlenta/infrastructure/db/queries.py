"""Read side: готовые DTO одним SQL-запросом, без загрузки доменных сущностей."""

from datetime import date, datetime, time, tzinfo
from uuid import UUID

import asyncpg

from studlenta.application.dto import (
    AuthoredEvent,
    CalendarDay,
    EventDetails,
    FeedItem,
    MyEventItem,
)
from studlenta.application.ports import FeedQuery
from studlenta.domain.events import EventStatus
from studlenta.infrastructure.db.repositories import Conn, category_ref

# $viewer — всегда последний параметр запроса; NULL для гостя.
_FEED_SELECT = """
SELECT e.id, e.title, e.summary, e.place, e.starts_at, e.ends_at, e.cover_url,
       c.id AS c_id, c.slug AS c_slug, c.name AS c_name, c.color AS c_color,
       (SELECT count(*) FROM likes l WHERE l.event_id = e.id) AS likes_count,
       EXISTS (SELECT 1 FROM likes l WHERE l.event_id = e.id AND l.user_id = {viewer}) AS liked,
       EXISTS (SELECT 1 FROM favorites f
               WHERE f.event_id = e.id AND f.user_id = {viewer}) AS favorited
"""


def _feed_item(r: asyncpg.Record) -> FeedItem:
    return FeedItem(
        id=r["id"],
        title=r["title"],
        summary=r["summary"],
        place=r["place"],
        starts_at=r["starts_at"],
        ends_at=r["ends_at"],
        cover_url=r["cover_url"],
        category=category_ref(r, "c_"),
        likes_count=r["likes_count"],
        liked=r["liked"],
        favorited=r["favorited"],
    )


_AUTHORED_SELECT = """
SELECT e.*, u.full_name AS author_name,
       c.id AS c_id, c.slug AS c_slug, c.name AS c_name, c.color AS c_color
FROM events e
JOIN users u ON u.id = e.author_id
LEFT JOIN categories c ON c.id = e.category_id
"""


def _authored(r: asyncpg.Record) -> AuthoredEvent:
    status = EventStatus(r["status"])
    return AuthoredEvent(
        id=r["id"],
        author_id=r["author_id"],
        author_name=r["author_name"],
        status=status,
        title=r["title"],
        summary=r["summary"],
        body=r["body"],
        category=category_ref(r, "c_") if r["c_id"] is not None else None,
        place=r["place"],
        starts_at=r["starts_at"],
        ends_at=r["ends_at"],
        cover_url=r["cover_url"],
        moderator_note=r["moderator_note"],
        submitted_at=r["submitted_at"],
        updated_at=r["updated_at"],
        is_resubmission=status is EventStatus.PENDING and r["moderator_note"] is not None,
    )


def _tz_name(tz: tzinfo) -> str:
    return str(getattr(tz, "key", None) or tz)


class PgEventQueries:
    def __init__(self, conn: Conn) -> None:
        self._conn = conn

    async def feed(self, query: FeedQuery, viewer_id: UUID | None) -> list[FeedItem]:
        after_at, after_id = query.after or (None, None)
        rows = await self._conn.fetch(
            _FEED_SELECT.format(viewer="$9")
            + """
            FROM events e JOIN categories c ON c.id = e.category_id
            WHERE e.status = 'published'
              AND e.starts_at >= $1
              AND ($2::timestamptz IS NULL OR e.starts_at < $2)
              AND ($3::text IS NULL OR c.slug = $3)
              AND ($4::text IS NULL OR e.search @@ websearch_to_tsquery('russian', $4))
              AND ($5::uuid IS NULL OR EXISTS (
                    SELECT 1 FROM favorites f WHERE f.event_id = e.id AND f.user_id = $5))
              AND ($6::timestamptz IS NULL OR (e.starts_at, e.id) > ($6, $7::uuid))
            ORDER BY e.starts_at, e.id
            LIMIT $8
            """,
            query.starts_from, query.starts_before, query.category_slug, query.search,
            query.favorites_of, after_at, after_id, query.limit, viewer_id,
        )  # fmt: skip
        return [_feed_item(r) for r in rows]

    async def published(self, event_id: UUID, viewer_id: UUID | None) -> EventDetails | None:
        row = await self._conn.fetchrow(
            _FEED_SELECT.format(viewer="$2")
            + """, e.body, e.published_at, u.full_name AS organizer
            FROM events e
            JOIN categories c ON c.id = e.category_id
            JOIN users u ON u.id = e.author_id
            WHERE e.id = $1 AND e.status = 'published'
            """,
            event_id, viewer_id,
        )  # fmt: skip
        if row is None:
            return None
        return EventDetails(_feed_item(row), row["body"], row["organizer"], row["published_at"])

    async def similar(
        self, event_id: UUID, starts_from: datetime, viewer_id: UUID | None, limit: int
    ) -> list[FeedItem]:
        rows = await self._conn.fetch(
            _FEED_SELECT.format(viewer="$4")
            + """
            FROM events e JOIN categories c ON c.id = e.category_id
            WHERE e.status = 'published' AND e.id <> $1 AND e.starts_at >= $2
              AND e.category_id = (SELECT category_id FROM events WHERE id = $1)
            ORDER BY e.starts_at, e.id
            LIMIT $3
            """,
            event_id, starts_from, limit, viewer_id,
        )  # fmt: skip
        return [_feed_item(r) for r in rows]

    async def authored(self, event_id: UUID) -> AuthoredEvent | None:
        row = await self._conn.fetchrow(_AUTHORED_SELECT + " WHERE e.id = $1", event_id)
        return _authored(row) if row else None

    async def by_author(self, author_id: UUID, status: EventStatus | None) -> list[MyEventItem]:
        rows = await self._conn.fetch(
            """
            SELECT e.id, e.title, e.status, e.cover_url, e.starts_at, e.updated_at,
                   e.moderator_note,
                   (SELECT count(*) FROM likes l WHERE l.event_id = e.id) AS likes_count,
                   (SELECT count(*) FROM favorites f WHERE f.event_id = e.id) AS favorites_count
            FROM events e
            WHERE e.author_id = $1 AND ($2::event_status IS NULL OR e.status = $2)
            ORDER BY e.updated_at DESC, e.id
            """,
            author_id, status.value if status else None,
        )  # fmt: skip
        return [
            MyEventItem(r["id"], r["title"], EventStatus(r["status"]), r["cover_url"],
                        r["starts_at"], r["updated_at"], r["moderator_note"], r["likes_count"],
                        r["favorites_count"])
            for r in rows
        ]  # fmt: skip

    async def moderation_queue(self, status: EventStatus) -> list[AuthoredEvent]:
        # Очередь честная: кто раньше отправил — того раньше смотрят. Решённые — свежие сверху.
        order = (
            "e.submitted_at, e.id"
            if status in (EventStatus.PENDING, EventStatus.CHANGES_REQUESTED)
            else "e.updated_at DESC, e.id"
        )
        rows = await self._conn.fetch(
            f"{_AUTHORED_SELECT} WHERE e.status = $1 ORDER BY {order}", status.value
        )
        return [_authored(r) for r in rows]

    async def calendar_month(self, year: int, month: int, tz: tzinfo) -> list[CalendarDay]:
        start = datetime.combine(date(year, month, 1), time.min, tzinfo=tz)
        nxt = date(year + month // 12, month % 12 + 1, 1)
        end = datetime.combine(nxt, time.min, tzinfo=tz)
        rows = await self._conn.fetch(
            """
            SELECT (e.starts_at AT TIME ZONE $3)::date AS day,
                   count(*) AS count,
                   (array_agg(e.title ORDER BY e.starts_at, e.id))[1:2] AS titles,
                   (array_agg(c.color ORDER BY e.starts_at, e.id))[1:2] AS colors
            FROM events e JOIN categories c ON c.id = e.category_id
            WHERE e.status = 'published' AND e.starts_at >= $1 AND e.starts_at < $2
            GROUP BY 1
            ORDER BY 1
            """,
            start, end, _tz_name(tz),
        )  # fmt: skip
        return [
            CalendarDay(r["day"], r["count"], list(zip(r["titles"], r["colors"], strict=True)))
            for r in rows
        ]
