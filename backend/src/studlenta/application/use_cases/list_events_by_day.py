"""Сценарий: события выбранного дня в календаре."""

from datetime import date, datetime, time, timedelta, tzinfo

from studlenta.application.dto import Actor, FeedItem
from studlenta.application.ports import FeedQuery, UnitOfWorkFactory

DAY_LIMIT = 50


class ListEventsByDay:
    def __init__(self, uow: UnitOfWorkFactory, tz: tzinfo) -> None:
        self._uow, self._tz = uow, tz

    async def __call__(self, day: date, viewer: Actor | None) -> list[FeedItem]:
        start = datetime.combine(day, time.min, tzinfo=self._tz)
        query = FeedQuery(
            starts_from=start, starts_before=start + timedelta(days=1), limit=DAY_LIMIT
        )
        async with self._uow() as uow:
            return await uow.queries.feed(query, viewer.user_id if viewer else None)
