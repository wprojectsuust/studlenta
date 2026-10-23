from dataclasses import replace
from datetime import date, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from studlenta.application.dto import CandidateItem, CategoryRef, HistoryItem
from studlenta.application.use_cases.get_interest_analytics import GetInterestAnalytics
from studlenta.application.use_cases.list_recommendations import ListRecommendations
from studlenta.application.use_cases.record_event_view import RecordEventView
from studlenta.domain.errors import ValidationError
from studlenta.domain.recommendations import CoView, Interaction
from studlenta.domain.users import Role
from tests.fakes import NOW, FakeClock, FakeUnitOfWork
from tests.unit.application.conftest import add_user
from tests.unit.application.test_feed import item

UFA = ZoneInfo("Asia/Yekaterinburg")
VISITOR = UUID("6f1c2a52-3c1d-4f0e-9a49-1b7f3c1f0a11")
SPORT = CategoryRef(2, "sport", "Спорт", "#15803D")


class TestRecordView:
    async def test_guest_view_is_counted_once_a_day(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        uow.interests.published.add(UUID(int=1))
        record = RecordEventView(uow, clock, UFA)
        await record(UUID(int=1), None, VISITOR)
        await record(UUID(int=1), None, VISITOR)
        assert uow.interests.views == {(UUID(int=1), f"g:{VISITOR}", date(2026, 10, 23))}
        assert uow.commits == 2

    async def test_signed_in_view_is_tied_to_the_user(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        uow.interests.published.add(UUID(int=1))
        actor = await add_user(uow, 1)
        await RecordEventView(uow, clock, UFA)(UUID(int=1), actor, VISITOR)
        assert {v[1] for v in uow.interests.views} == {f"u:{actor.user_id}"}

    async def test_unpublished_event_is_ignored(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        await RecordEventView(uow, clock, UFA)(UUID(int=1), None, VISITOR)
        assert uow.interests.views == set()
        assert uow.commits == 0

    async def test_anonymous_without_visitor_id_is_rejected(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        with pytest.raises(ValidationError):
            await RecordEventView(uow, clock, UFA)(UUID(int=1), None, None)


def candidate(
    n: int, words: str, popularity: float = 0, category: CategoryRef | None = None
) -> CandidateItem:
    feed_item = item(n) if category is None else replace(item(n), category=category)
    return CandidateItem(feed_item, frozenset(words.split()), popularity)


def history(n: int, words: str, kind: str = "view", category: int = 1) -> HistoryItem:
    return HistoryItem(
        Interaction(UUID(int=n), category, frozenset(words.split()), kind, NOW - timedelta(days=1)),
        f"Прошлое {n}",
    )


class TestRecommendations:
    async def test_guest_without_history_gets_popular_with_explanation(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        uow.interests.candidates_result = [candidate(1, "лекция", 0), candidate(2, "концерт", 7)]
        recs = await ListRecommendations(uow, clock, UFA)(None, None)
        assert [(r.item.id, r.reason, r.reason_kind) for r in recs] == [
            (UUID(int=2), "Популярно у студентов", "popular"),
            (UUID(int=1), "Скоро", "soon"),
        ]
        assert uow.interests.calls[0][0] == "candidates"  # без зрителя историю не ищем

    async def test_reasons_name_the_category_and_past_events(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        uow.interests.history_result = [
            history(100, "джаз", "favorite"),
            history(101, "хакатон python", category=3),
        ]
        uow.interests.candidates_result = [
            candidate(1, "хор"),
            candidate(2, "хакатон python", category=SPORT),
            candidate(3, "футбол", category=SPORT),
        ]
        uow.interests.co_views_result = [CoView(UUID(int=3), UUID(int=100), 3)]
        recs = await ListRecommendations(uow, clock, UFA)(None, VISITOR)
        reasons = {r.item.id.int: r.reason for r in recs}
        assert reasons[1] == "Вы часто смотрите «Концерты»"
        assert reasons[2] == "Похоже на «Прошлое 101»"
        assert reasons[3] == "Смотрели те, кто смотрел «Прошлое 100»"
        [(_, (viewers, user_id, _since))] = [c for c in uow.interests.calls if c[0] == "history"]
        assert viewers == [f"g:{VISITOR}"]
        assert user_id is None

    async def test_signed_in_user_merges_guest_and_account_history(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        actor = await add_user(uow, 1)
        await ListRecommendations(uow, clock, UFA)(actor, VISITOR)
        [(_, (viewers, user_id, _))] = [c for c in uow.interests.calls if c[0] == "history"]
        assert viewers == [f"u:{actor.user_id}", f"g:{VISITOR}"]
        assert user_id == actor.user_id


class TestAnalytics:
    async def test_moderator_sees_the_whole_feed(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        mod = await add_user(uow, 1, Role.MODERATOR)
        await GetInterestAnalytics(uow, clock, UFA)(mod, days=7)
        [(_, (since, until, tz, author))] = uow.interests.calls
        assert author is None
        assert tz is UFA
        assert (since, until) == (NOW - timedelta(days=7), NOW)

    async def test_author_sees_only_own_events(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        author = await add_user(uow, 1)
        await GetInterestAnalytics(uow, clock, UFA)(author)
        [(_, (_, _, _, author_id))] = uow.interests.calls
        assert author_id == author.user_id

    @pytest.mark.parametrize("days", [0, 366])
    async def test_period_is_bounded(
        self, uow: FakeUnitOfWork, clock: FakeClock, days: int
    ) -> None:
        mod = await add_user(uow, 1, Role.MODERATOR)
        with pytest.raises(ValidationError):
            await GetInterestAnalytics(uow, clock, UFA)(mod, days=days)
