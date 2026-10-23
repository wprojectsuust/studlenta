"""Сценарий: сетка месяца в календаре — число событий и превью по дням."""

from datetime import tzinfo

from studlenta.application.caching import CALENDAR_TTL, NO_CACHE
from studlenta.application.dto import CalendarDay
from studlenta.application.ports import ReadCache, UnitOfWorkFactory
from studlenta.domain.errors import ValidationError


class GetCalendarMonth:
    def __init__(self, uow: UnitOfWorkFactory, tz: tzinfo, cache: ReadCache = NO_CACHE) -> None:
        self._uow, self._tz, self._cache = uow, tz, cache

    async def __call__(self, year: int, month: int) -> list[CalendarDay]:
        if not (2000 <= year <= 2100 and 1 <= month <= 12):
            raise ValidationError({"month": "Некорректный месяц"})

        async def load() -> list[CalendarDay]:
            async with self._uow() as uow:
                return await uow.queries.calendar_month(year, month, self._tz)

        return await self._cache.get_or_load(f"calendar:{year}-{month:02d}", CALENDAR_TTL, load)
