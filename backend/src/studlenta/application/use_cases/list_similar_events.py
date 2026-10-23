"""Сценарий: «Похожие события» — ближайшие из той же категории."""

from datetime import tzinfo
from uuid import UUID

from studlenta.application.dto import Actor, FeedItem
from studlenta.application.ports import Clock, UnitOfWorkFactory
from studlenta.domain.periods import Period, period_bounds


class ListSimilarEvents:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock, tz: tzinfo) -> None:
        self._uow, self._clock, self._tz = uow, clock, tz

    async def __call__(
        self, event_id: UUID, viewer: Actor | None, limit: int = 3
    ) -> list[FeedItem]:
        start, _ = period_bounds(Period.ALL, now=self._clock.now(), tz=self._tz)
        async with self._uow() as uow:
            return await uow.queries.similar(
                event_id, start, viewer.user_id if viewer else None, limit
            )
