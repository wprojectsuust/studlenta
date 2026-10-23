from uuid import UUID
from zoneinfo import ZoneInfo

from studlenta.application.dto import EventDetails
from studlenta.application.use_cases.approve_event import ApproveEvent
from studlenta.application.use_cases.archive_event import ArchiveEvent
from studlenta.application.use_cases.get_calendar_month import GetCalendarMonth
from studlenta.application.use_cases.get_published_event import GetPublishedEvent
from studlenta.application.use_cases.list_categories import ListCategories
from studlenta.application.use_cases.list_published_events import FeedParams, ListPublishedEvents
from studlenta.domain.users import Role
from studlenta.infrastructure.cache import TtlCache
from tests.fakes import FakeClock, FakeUnitOfWork, SequentialIds
from tests.unit.application.conftest import add_event, add_user
from tests.unit.application.test_feed import item

UFA = ZoneInfo("Asia/Yekaterinburg")


def count(uow: FakeUnitOfWork, name: str) -> int:
    return sum(1 for c, _ in uow.queries.calls if c == name)


async def test_guest_reads_are_cached(uow: FakeUnitOfWork, clock: FakeClock) -> None:
    cache = TtlCache()
    feed = ListPublishedEvents(uow, clock, UFA, cache)
    for _ in range(3):
        await feed(FeedParams(), viewer=None)
        await GetCalendarMonth(uow, UFA, cache)(2026, 10)
        await ListCategories(uow, clock, UFA, cache)()
    assert count(uow, "feed") == 1
    assert count(uow, "calendar_month") == 1
    assert len(uow.categories.calls) == 1


async def test_personal_reads_bypass_cache(uow: FakeUnitOfWork, clock: FakeClock) -> None:
    cache = TtlCache()
    viewer = await add_user(uow, 1)
    feed = ListPublishedEvents(uow, clock, UFA, cache)
    await feed(FeedParams(), viewer=viewer)
    await feed(FeedParams(), viewer=viewer)
    await feed(FeedParams(favorites_only=True), viewer=viewer)
    assert count(uow, "feed") == 3


async def test_different_filters_are_different_entries(
    uow: FakeUnitOfWork, clock: FakeClock
) -> None:
    cache = TtlCache()
    feed = ListPublishedEvents(uow, clock, UFA, cache)
    await feed(FeedParams(category="sport"), viewer=None)
    await feed(FeedParams(category="concerts"), viewer=None)
    await feed(FeedParams(category="sport"), viewer=None)
    assert count(uow, "feed") == 2


async def test_event_page_cached_for_guests_only(uow: FakeUnitOfWork) -> None:
    cache = TtlCache()
    uow.queries.published_result = EventDetails(item(1), "Описание", "Студсовет", item(1).starts_at)
    viewer = await add_user(uow, 1)
    for _ in range(2):
        await GetPublishedEvent(uow, cache)(UUID(int=1), viewer=None)
        await GetPublishedEvent(uow, cache)(UUID(int=1), viewer=viewer)
    assert count(uow, "published") == 3


async def test_publishing_and_archiving_reset_public_cache(
    uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds
) -> None:
    cache = TtlCache()
    feed = ListPublishedEvents(uow, clock, UFA, cache)
    author, moderator = await add_user(uow, 1), await add_user(uow, 2, Role.MODERATOR)
    event = await add_event(uow, author, state="pending")

    await feed(FeedParams(), viewer=None)
    await ApproveEvent(uow, clock, ids, cache)(moderator, event.id)
    await feed(FeedParams(), viewer=None)
    await ArchiveEvent(uow, clock, cache)(author, event.id)
    await feed(FeedParams(), viewer=None)
    assert count(uow, "feed") == 3
