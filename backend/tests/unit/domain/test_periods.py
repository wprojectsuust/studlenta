from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from studlenta.domain.periods import Period, period_bounds

UFA = ZoneInfo("Asia/Yekaterinburg")
# Пятница, 23 октября 2026, 02:30 по Уфе — 21:30 22 октября по UTC: проверяем, что «сегодня»
# считается по местному времени, а не по UTC.
NOW = datetime(2026, 10, 22, 21, 30, tzinfo=UTC)


def local(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=UFA)


@pytest.mark.parametrize(
    ("period", "end"),
    [
        (Period.TODAY, local(2026, 10, 24)),
        (Period.WEEK, local(2026, 10, 26)),  # до понедельника
        (Period.MONTH, local(2026, 11, 1)),
        (Period.ALL, None),
    ],
)
def test_bounds_start_at_local_midnight(period: Period, end: datetime | None) -> None:
    start, actual_end = period_bounds(period, now=NOW, tz=UFA)
    assert start == local(2026, 10, 23)
    assert actual_end == end


def test_week_on_sunday_ends_next_midnight() -> None:
    sunday = datetime(2026, 10, 25, 12, 0, tzinfo=UFA)
    _, end = period_bounds(Period.WEEK, now=sunday, tz=UFA)
    assert end == local(2026, 10, 26)


def test_month_in_december_rolls_over_year() -> None:
    _, end = period_bounds(Period.MONTH, now=datetime(2026, 12, 15, tzinfo=UFA), tz=UFA)
    assert end == local(2027, 1, 1)


def test_naive_now_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone"):
        period_bounds(Period.TODAY, now=datetime(2026, 10, 23), tz=UFA)  # noqa: DTZ001
