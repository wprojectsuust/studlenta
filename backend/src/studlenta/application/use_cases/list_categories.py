"""Сценарий: категории с числом предстоящих событий (сайдбар)."""

from datetime import tzinfo

from studlenta.application.caching import CATEGORIES_TTL, NO_CACHE
from studlenta.application.dto import CategoryWithCount
from studlenta.application.ports import Clock, ReadCache, UnitOfWorkFactory
from studlenta.domain.periods import Period, period_bounds


class ListCategories:
    def __init__(
        self, uow: UnitOfWorkFactory, clock: Clock, tz: tzinfo, cache: ReadCache = NO_CACHE
    ) -> None:
        self._uow, self._clock, self._tz, self._cache = uow, clock, tz, cache

    async def __call__(self) -> list[CategoryWithCount]:
        start, _ = period_bounds(Period.ALL, now=self._clock.now(), tz=self._tz)

        async def load() -> list[CategoryWithCount]:
            async with self._uow() as uow:
                return await uow.categories.list_with_counts(start)

        return await self._cache.get_or_load(f"categories:{start.date()}", CATEGORIES_TTL, load)
