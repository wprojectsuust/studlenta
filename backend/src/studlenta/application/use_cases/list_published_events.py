"""Сценарий: лента опубликованных событий с фильтрами по времени, категории и поиску."""

from dataclasses import dataclass
from datetime import tzinfo

from studlenta.application.caching import FEED_TTL, NO_CACHE
from studlenta.application.dto import Actor, FeedItem, Page
from studlenta.application.pagination import decode_cursor, encode_cursor
from studlenta.application.ports import Clock, FeedQuery, ReadCache, UnitOfWorkFactory
from studlenta.domain.errors import AuthenticationError
from studlenta.domain.periods import Period, period_bounds

MAX_LIMIT = 50
SEARCH_MAX = 100


@dataclass(frozen=True, slots=True)
class FeedParams:
    period: Period = Period.ALL
    category: str | None = None
    search: str | None = None
    favorites_only: bool = False
    cursor: str | None = None
    limit: int = 20


class ListPublishedEvents:
    def __init__(
        self, uow: UnitOfWorkFactory, clock: Clock, tz: tzinfo, cache: ReadCache = NO_CACHE
    ) -> None:
        self._uow, self._clock, self._tz, self._cache = uow, clock, tz, cache

    async def __call__(self, params: FeedParams, viewer: Actor | None) -> Page[FeedItem]:
        if params.favorites_only and viewer is None:
            raise AuthenticationError("Избранное на сервере доступно после входа")
        start, end = period_bounds(params.period, now=self._clock.now(), tz=self._tz)
        limit = max(1, min(params.limit, MAX_LIMIT))
        search = (params.search or "").strip()[:SEARCH_MAX] or None
        query = FeedQuery(
            starts_from=start,
            starts_before=end,
            category_slug=params.category or None,
            search=search,
            favorites_of=viewer.user_id if params.favorites_only and viewer else None,
            after=decode_cursor(params.cursor) if params.cursor is not None else None,
            limit=limit + 1,
        )

        async def load() -> list[FeedItem]:
            async with self._uow() as uow:
                return await uow.queries.feed(query, viewer.user_id if viewer else None)

        if viewer is None:  # гостевая лента одинакова для всех — её и кешируем
            key = ":".join(
                str(part)
                for part in ("feed", query.starts_from.isoformat(), query.starts_before,
                             query.category_slug, query.search, query.after, query.limit)
            )  # fmt: skip
            rows = await self._cache.get_or_load(key, FEED_TTL, load)
        else:
            rows = await load()
        items = rows[:limit]
        has_more = len(rows) > limit
        cursor = encode_cursor(items[-1].starts_at, items[-1].id) if has_more else None
        return Page(items=items, next_cursor=cursor)
