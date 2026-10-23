from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from studlenta.application.dto import EventDetails, FeedItem
from studlenta.application.pagination import encode_cursor
from studlenta.application.use_cases.get_calendar_month import GetCalendarMonth
from studlenta.application.use_cases.get_event_ics import GetEventIcs
from studlenta.application.use_cases.get_published_event import GetPublishedEvent
from studlenta.application.use_cases.list_categories import ListCategories
from studlenta.application.use_cases.list_events_by_day import ListEventsByDay
from studlenta.application.use_cases.list_published_events import FeedParams, ListPublishedEvents
from studlenta.application.use_cases.list_similar_events import ListSimilarEvents
from studlenta.domain.errors import AuthenticationError, NotFoundError, ValidationError
from studlenta.domain.periods import Period
from tests.fakes import NOW, FakeClock, FakeUnitOfWork, category_ref
from tests.unit.application.conftest import add_user

UFA = ZoneInfo("Asia/Yekaterinburg")


def item(n: int, starts_at: datetime | None = None) -> FeedItem:
    return FeedItem(
        id=UUID(int=n),
        title=f"Событие {n}",
        summary="Анонс",
        place="Зал",
        starts_at=starts_at or NOW + timedelta(hours=n),
        ends_at=None,
        cover_url=None,
        category=category_ref(),
        likes_count=0,
        liked=False,
        favorited=False,
    )


def feed(uow: FakeUnitOfWork, clock: FakeClock) -> ListPublishedEvents:
    return ListPublishedEvents(uow, clock, UFA)


class TestFeed:
    async def test_period_becomes_local_bounds(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        await feed(uow, clock)(FeedParams(period=Period.TODAY), viewer=None)
        [(_, (query, viewer))] = uow.queries.calls
        assert query.starts_from == datetime(2026, 10, 23, tzinfo=UFA)
        assert query.starts_before == datetime(2026, 10, 24, tzinfo=UFA)
        assert viewer is None

    async def test_next_cursor_when_more_items_exist(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        uow.queries.feed_result = [item(n) for n in range(1, 4)]
        page = await feed(uow, clock)(FeedParams(limit=2), viewer=None)
        assert [i.id for i in page.items] == [UUID(int=1), UUID(int=2)]
        assert page.next_cursor == encode_cursor(page.items[-1].starts_at, page.items[-1].id)
        [(_, (query, _))] = uow.queries.calls
        assert query.limit == 3  # на один больше, чтобы понять, есть ли следующая страница

    async def test_last_page_has_no_cursor(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        uow.queries.feed_result = [item(1)]
        page = await feed(uow, clock)(FeedParams(limit=2), viewer=None)
        assert page.next_cursor is None

    async def test_cursor_is_decoded_for_keyset(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        cursor = encode_cursor(NOW, UUID(int=7))
        await feed(uow, clock)(FeedParams(cursor=cursor), viewer=None)
        assert uow.queries.calls[0][1][0].after == (NOW, UUID(int=7))

    @pytest.mark.parametrize("cursor", ["garbage", "Zm9v", ""])
    async def test_broken_cursor(self, uow: FakeUnitOfWork, clock: FakeClock, cursor: str) -> None:
        with pytest.raises(ValidationError) as exc:
            await feed(uow, clock)(FeedParams(cursor=cursor), viewer=None)
        assert "cursor" in exc.value.fields

    async def test_search_and_limit_are_sanitized(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        await feed(uow, clock)(FeedParams(search="   ", limit=500, category="sport"), viewer=None)
        query = uow.queries.calls[0][1][0]
        assert query.search is None
        assert query.limit == 51
        assert query.category_slug == "sport"

    async def test_favorites_need_login(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        with pytest.raises(AuthenticationError):
            await feed(uow, clock)(FeedParams(favorites_only=True), viewer=None)

    async def test_favorites_of_viewer(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        viewer = await add_user(uow, 1)
        await feed(uow, clock)(FeedParams(favorites_only=True), viewer=viewer)
        query, viewer_id = uow.queries.calls[0][1]
        assert query.favorites_of == viewer.user_id == viewer_id


class TestEventPage:
    async def test_not_published_is_not_found(self, uow: FakeUnitOfWork) -> None:
        with pytest.raises(NotFoundError):
            await GetPublishedEvent(uow)(UUID(int=1), viewer=None)

    async def test_similar_upcoming_only(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        await ListSimilarEvents(uow, clock, UFA)(UUID(int=1), viewer=None)
        assert uow.queries.calls == [
            ("similar", (UUID(int=1), datetime(2026, 10, 23, tzinfo=UFA), None, 3))
        ]

    async def test_ics_export(self, uow: FakeUnitOfWork) -> None:
        uow.queries.published_result = EventDetails(
            item=item(1, starts_at=datetime(2026, 10, 23, 13, 0, tzinfo=UFA)),
            body="Описание; с запятой, и переносом\nстроки",
            organizer_name="Студсовет",
            published_at=NOW,
        )
        ics = await GetEventIcs(uow)(UUID(int=1))
        assert ics.startswith("BEGIN:VCALENDAR\r\n")
        assert "DTSTART:20261023T080000Z\r\n" in ics
        assert "DTEND:20261023T090000Z\r\n" in ics  # без окончания — час
        assert "DESCRIPTION:Описание\\; с запятой\\, и переносом\\nстроки" in ics
        assert ics.endswith("END:VCALENDAR\r\n")


class TestCalendarAndCategories:
    async def test_month_validated(self, uow: FakeUnitOfWork) -> None:
        with pytest.raises(ValidationError):
            await GetCalendarMonth(uow, UFA)(2026, 13)
        await GetCalendarMonth(uow, UFA)(2026, 10)
        assert uow.queries.calls == [("calendar_month", (2026, 10, UFA))]

    async def test_day_uses_local_bounds(self, uow: FakeUnitOfWork) -> None:
        await ListEventsByDay(uow, UFA)(date(2026, 10, 29), viewer=None)
        query = uow.queries.calls[0][1][0]
        assert query.starts_from == datetime(2026, 10, 29, tzinfo=UFA)
        assert query.starts_before == datetime(2026, 10, 30, tzinfo=UFA)

    async def test_category_counts_from_start_of_today(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        await ListCategories(uow, clock, UFA)()
        assert uow.categories.calls == [datetime(2026, 10, 23, tzinfo=UFA)]
