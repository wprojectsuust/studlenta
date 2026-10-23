"""Временные группы ленты: «Сегодня», «На этой неделе», «В этом месяце».

Границы считаются по местному времени университета, а не по UTC: событие в 01:00 по Уфе
относится к «сегодня», хотя в UTC это ещё вчера.
"""

from datetime import datetime, time, timedelta, tzinfo
from enum import StrEnum


class Period(StrEnum):
    ALL = "all"
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"


def period_bounds(period: Period, *, now: datetime, tz: tzinfo) -> tuple[datetime, datetime | None]:
    """Полуинтервал [start, end) для фильтра; ``end is None`` — без верхней границы."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    today = now.astimezone(tz).date()
    start = datetime.combine(today, time.min, tzinfo=tz)
    match period:
        case Period.ALL:
            return start, None
        case Period.TODAY:
            return start, start + timedelta(days=1)
        case Period.WEEK:
            return start, start + timedelta(days=7 - today.weekday())
        case Period.MONTH:
            first_next = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
            return start, datetime.combine(first_next, time.min, tzinfo=tz)
