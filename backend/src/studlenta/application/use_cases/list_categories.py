"""Сценарий: категории с числом предстоящих событий (сайдбар)."""

from datetime import tzinfo

from studlenta.application.dto import CategoryWithCount
from studlenta.application.ports import Clock, UnitOfWorkFactory
from studlenta.domain.periods import Period, period_bounds


class ListCategories:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock, tz: tzinfo) -> None:
        self._uow, self._clock, self._tz = uow, clock, tz

    async def __call__(self) -> list[CategoryWithCount]:
        start, _ = period_bounds(Period.ALL, now=self._clock.now(), tz=self._tz)
        async with self._uow() as uow:
            return await uow.categories.list_with_counts(start)
