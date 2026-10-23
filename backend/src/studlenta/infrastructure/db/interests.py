"""Сигналы интереса: просмотры, выборки для рекомендаций и отчёт для аналитики."""

from collections.abc import Sequence
from datetime import date, datetime, tzinfo
from uuid import UUID

from studlenta.application.dto import (
    CandidateItem,
    CategoryInterest,
    DailyViews,
    EventInterest,
    HistoryItem,
    InterestReport,
    InterestTotals,
)
from studlenta.domain.recommendations import CoView, Interaction
from studlenta.infrastructure.db.queries import _FEED_SELECT, _feed_item, _tz_name
from studlenta.infrastructure.db.repositories import Conn, category_ref

TOP_EVENTS = 10

# Активность по каждому событию в области видимости за [$1, $2]; $3 — автор или NULL.
_EVENT_STATS = """
SELECT e.id, e.title, e.starts_at, c.id AS c_id, c.slug AS c_slug, c.name AS c_name,
       c.color AS c_color,
       (SELECT count(*) FROM event_views v
        WHERE v.event_id = e.id AND v.viewed_at >= $1 AND v.viewed_at <= $2) AS views,
       (SELECT count(DISTINCT v.viewer) FROM event_views v
        WHERE v.event_id = e.id AND v.viewed_at >= $1 AND v.viewed_at <= $2) AS viewers,
       (SELECT count(*) FROM likes l
        WHERE l.event_id = e.id AND l.created_at >= $1 AND l.created_at <= $2) AS likes,
       (SELECT count(*) FROM favorites f
        WHERE f.event_id = e.id AND f.created_at >= $1 AND f.created_at <= $2) AS favorites
FROM events e JOIN categories c ON c.id = e.category_id
WHERE e.status IN ('published', 'archived') AND ($3::uuid IS NULL OR e.author_id = $3)
"""


class PgInterestQueries:
    def __init__(self, conn: Conn) -> None:
        self._conn = conn

    async def record_view(
        self, event_id: UUID, viewer: str, user_id: UUID | None, day: date, now: datetime
    ) -> bool:
        published: bool = await self._conn.fetchval(
            """
            WITH ev AS (SELECT id FROM events WHERE id = $1 AND status = 'published'),
            ins AS (
                INSERT INTO event_views (event_id, viewer, user_id, viewed_on, viewed_at)
                SELECT id, $2, $3, $4, $5 FROM ev
                ON CONFLICT DO NOTHING
            )
            SELECT EXISTS (SELECT 1 FROM ev)
            """,
            event_id, viewer, user_id, day, now,
        )  # fmt: skip
        return published

    async def history(
        self, viewers: Sequence[str], user_id: UUID | None, since: datetime
    ) -> list[HistoryItem]:
        rows = await self._conn.fetch(
            """
            WITH signals AS (
                SELECT event_id, 'view' AS kind, viewed_at AS at FROM event_views
                WHERE viewer = ANY($1::text[]) AND viewed_at >= $3
                UNION ALL
                SELECT event_id, 'like', created_at FROM likes
                WHERE user_id = $2 AND created_at >= $3
                UNION ALL
                SELECT event_id, 'favorite', created_at FROM favorites
                WHERE user_id = $2 AND created_at >= $3
            )
            SELECT s.event_id, s.kind, s.at, e.category_id, e.title,
                   tsvector_to_array(e.search) AS lexemes
            FROM signals s JOIN events e ON e.id = s.event_id
            WHERE e.category_id IS NOT NULL
            ORDER BY s.at DESC
            LIMIT 500
            """,
            list(viewers), user_id, since,
        )  # fmt: skip
        return [
            HistoryItem(
                Interaction(
                    r["event_id"], r["category_id"], frozenset(r["lexemes"]), r["kind"], r["at"]
                ),
                r["title"],
            )
            for r in rows
        ]

    async def candidates(
        self, starts_from: datetime, viewer_id: UUID | None, since: datetime, limit: int
    ) -> list[CandidateItem]:
        rows = await self._conn.fetch(
            _FEED_SELECT.format(viewer="$4")
            + """, tsvector_to_array(e.search) AS lexemes,
              (SELECT count(*) FROM event_views v WHERE v.event_id = e.id AND v.viewed_at >= $2)
              + 3 * (SELECT count(*) FROM likes l WHERE l.event_id = e.id AND l.created_at >= $2)
              + 5 * (SELECT count(*) FROM favorites f
                     WHERE f.event_id = e.id AND f.created_at >= $2) AS popularity
            FROM events e JOIN categories c ON c.id = e.category_id
            WHERE e.status = 'published' AND e.starts_at >= $1
            ORDER BY e.starts_at, e.id
            LIMIT $3
            """,
            starts_from, since, limit, viewer_id,
        )  # fmt: skip
        return [
            CandidateItem(_feed_item(r), frozenset(r["lexemes"]), float(r["popularity"]))
            for r in rows
        ]

    async def co_views(
        self, seeds: Sequence[UUID], viewers: Sequence[str], since: datetime
    ) -> list[CoView]:
        rows = await self._conn.fetch(
            """
            SELECT other.event_id, mine.event_id AS seed_id,
                   count(DISTINCT other.viewer) AS viewers
            FROM event_views mine
            JOIN event_views other
              ON other.viewer = mine.viewer AND other.event_id <> mine.event_id
            WHERE mine.event_id = ANY($1::uuid[]) AND mine.viewer <> ALL($2::text[])
              AND mine.viewed_at >= $3 AND other.viewed_at >= $3
            GROUP BY other.event_id, mine.event_id
            """,
            list(seeds), list(viewers), since,
        )  # fmt: skip
        return [CoView(r["event_id"], r["seed_id"], r["viewers"]) for r in rows]

    async def report(
        self, since: datetime, until: datetime, tz: tzinfo, author_id: UUID | None
    ) -> InterestReport:
        per_event = await self._conn.fetch(
            _EVENT_STATS + " ORDER BY e.starts_at", since, until, author_id
        )
        totals = await self._conn.fetchrow(
            """
            SELECT
              (SELECT count(*) FROM event_views v JOIN events e ON e.id = v.event_id
               WHERE v.viewed_at >= $1 AND v.viewed_at <= $2
                 AND ($3::uuid IS NULL OR e.author_id = $3)) AS views,
              (SELECT count(DISTINCT v.viewer) FROM event_views v JOIN events e ON e.id = v.event_id
               WHERE v.viewed_at >= $1 AND v.viewed_at <= $2
                 AND ($3::uuid IS NULL OR e.author_id = $3)) AS viewers
            """,
            since, until, author_id,
        )  # fmt: skip
        daily = await self._conn.fetch(
            """
            SELECT d::date AS day, count(v.viewer) AS views, count(DISTINCT v.viewer) AS viewers
            FROM generate_series(
                ($1 AT TIME ZONE $4)::date, ($2 AT TIME ZONE $4)::date, interval '1 day'
            ) AS d
            LEFT JOIN (
                event_views v JOIN events e
                ON e.id = v.event_id AND ($3::uuid IS NULL OR e.author_id = $3)
            ) ON v.viewed_on = d::date AND v.viewed_at >= $1 AND v.viewed_at <= $2
            GROUP BY d ORDER BY d
            """,
            since, until, author_id, _tz_name(tz),
        )  # fmt: skip
        events = [
            EventInterest(
                r["id"],
                r["title"],
                category_ref(r, "c_"),
                r["starts_at"],
                r["views"],
                r["viewers"],
                r["likes"],
                r["favorites"],
            )
            for r in per_event
        ]
        return InterestReport(
            scope="all" if author_id is None else "mine",
            days=(until - since).days,
            totals=InterestTotals(
                totals["views"] if totals else 0,
                totals["viewers"] if totals else 0,
                sum(e.likes for e in events),
                sum(e.favorites for e in events),
            ),
            daily=[DailyViews(r["day"], r["views"], r["viewers"]) for r in daily],
            categories=_by_category(events, since),
            top=sorted(
                (e for e in events if e.views or e.likes or e.favorites),
                key=lambda e: (e.views, e.favorites, e.likes),
                reverse=True,
            )[:TOP_EVENTS],
        )


def _by_category(events: list[EventInterest], since: datetime) -> list[CategoryInterest]:
    groups: dict[int, list[EventInterest]] = {}
    for e in events:
        groups.setdefault(e.category.id, []).append(e)
    out = [
        CategoryInterest(
            items[0].category,
            # Событий в категории: с активностью за период или ещё не прошедших к его началу.
            sum(1 for e in items if e.starts_at >= since or e.views or e.likes or e.favorites),
            sum(e.views for e in items),
            sum(e.likes for e in items),
            sum(e.favorites for e in items),
        )
        for items in groups.values()
    ]
    return sorted(out, key=lambda c: (c.views, c.favorites), reverse=True)
