"""Сценарий: сетка месяца в календаре — число событий и превью по дням."""

from datetime import tzinfo

from studlenta.application.dto import CalendarDay
from studlenta.application.ports import UnitOfWorkFactory
from studlenta.domain.errors import ValidationError


class GetCalendarMonth:
    def __init__(self, uow: UnitOfWorkFactory, tz: tzinfo) -> None:
        self._uow, self._tz = uow, tz

    async def __call__(self, year: int, month: int) -> list[CalendarDay]:
        if not (2000 <= year <= 2100 and 1 <= month <= 12):
            raise ValidationError({"month": "Некорректный месяц"})
        async with self._uow() as uow:
            return await uow.queries.calendar_month(year, month, self._tz)
