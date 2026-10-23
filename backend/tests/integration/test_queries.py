from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import asyncpg
import pytest

from studlenta.application.ports import FeedQuery
from studlenta.domain.events import EventStatus
from studlenta.domain.users import Role
from studlenta.infrastructure.db.uow import PostgresUnitOfWork
from tests.fakes import NOW
from tests.integration.conftest import make_event, make_user

pytestmark = pytest.mark.integration
UFA = ZoneInfo("Asia/Yekaterinburg")


def q(**kw: object) -> FeedQuery:
    data: dict[str, object] = {"starts_from": NOW, "starts_before": None}
    data.update(kw)
    return FeedQuery(**data)  # type: ignore[arg-type]


class TestFeed:
    async def test_only_published_upcoming_in_date_order(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author = await make_user(pool)
        late = await make_event(pool, author, starts_in=timedelta(days=5), title="Позже")
        early = await make_event(pool, author, starts_in=timedelta(days=1), title="Раньше")
        for status in ("draft", "pending", "rejected", "archived", "changes_requested"):
            await make_event(pool, author, status=status)
        await make_event(pool, author, starts_in=-timedelta(days=1), title="Прошло")
        async with uow() as tx:
            items = await tx.queries.feed(q(), None)
        assert [i.id for i in items] == [early.id, late.id]
        assert items[0].category.slug == "concerts"
        assert items[0].category.color == "#7C3AED"

    async def test_period_upper_bound_is_exclusive(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author = await make_user(pool)
        inside = await make_event(pool, author, starts_in=timedelta(hours=23))
        await make_event(pool, author, starts_in=timedelta(hours=24))
        async with uow() as tx:
            items = await tx.queries.feed(q(starts_before=NOW + timedelta(hours=24)), None)
        assert [i.id for i in items] == [inside.id]

    async def test_category_filter(self, pool: asyncpg.Pool, uow: PostgresUnitOfWork) -> None:
        author = await make_user(pool)
        sport = await make_event(pool, author, category="sport", title="Мини-футбол")
        await make_event(pool, author, category="concerts")
        async with uow() as tx:
            items = await tx.queries.feed(q(category_slug="sport"), None)
        assert [i.id for i in items] == [sport.id]

    async def test_search_understands_russian_word_forms(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author = await make_user(pool)
        concert = await make_event(pool, author, title="Большой концерт студентов")
        await make_event(pool, author, title="Турнир по мини-футболу", summary="Спорт")
        async with uow() as tx:
            by_title = await tx.queries.feed(q(search="концерты"), None)
            by_summary = await tx.queries.feed(q(search="хиты"), None)
            garbage = await tx.queries.feed(q(search="!!! & | :"), None)
        assert [i.id for i in by_title] == [concert.id]
        assert concert.id in {i.id for i in by_summary}
        assert garbage == []

    async def test_keyset_pagination_is_stable_for_equal_times(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author = await make_user(pool)
        same = timedelta(days=1)
        ids = sorted(
            [
                (await make_event(pool, author, starts_in=same, event_id=UUID(int=n))).id
                for n in (3, 1, 2)
            ]
        )
        async with uow() as tx:
            first = await tx.queries.feed(q(limit=2), None)
            rest = await tx.queries.feed(
                q(limit=2, after=(first[-1].starts_at, first[-1].id)), None
            )
        assert [i.id for i in first + rest] == ids

    async def test_viewer_flags_and_like_counts(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author, viewer, other = [await make_user(pool) for _ in range(3)]
        event = await make_event(pool, author)
        async with uow() as tx:
            await tx.reactions.like(viewer.id, event.id, NOW)
            await tx.reactions.like(other.id, event.id, NOW)
            await tx.reactions.favorite(viewer.id, event.id, NOW)
            await tx.commit()
        async with uow() as tx:
            [mine] = await tx.queries.feed(q(), viewer.id)
            [guest] = await tx.queries.feed(q(), None)
            favorites = await tx.queries.feed(q(favorites_of=viewer.id), viewer.id)
            none = await tx.queries.feed(q(favorites_of=other.id), other.id)
        assert (mine.likes_count, mine.liked, mine.favorited) == (2, True, True)
        assert (guest.likes_count, guest.liked, guest.favorited) == (2, False, False)
        assert [f.id for f in favorites] == [event.id]
        assert none == []


class TestEventPages:
    async def test_published_details_and_hidden_statuses(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author = await make_user(pool, name="Студсовет УУНиТ")
        event = await make_event(pool, author)
        pending = await make_event(pool, author, status="pending")
        async with uow() as tx:
            details = await tx.queries.published(event.id, None)
            assert await tx.queries.published(pending.id, None) is None
        assert details is not None
        assert details.organizer_name == "Студсовет УУНиТ"
        assert details.body.startswith("Подробное описание")
        assert details.published_at == event.published_at

    async def test_similar_same_category_excluding_itself(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author = await make_user(pool)
        event = await make_event(pool, author)
        twin = await make_event(pool, author, starts_in=timedelta(days=3))
        await make_event(pool, author, category="sport")
        await make_event(pool, author, starts_in=-timedelta(days=2))
        async with uow() as tx:
            similar = await tx.queries.similar(event.id, NOW, None, 3)
        assert [s.id for s in similar] == [twin.id]

    async def test_authored_and_by_author(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author = await make_user(pool, name="Иван")
        returned = await make_event(pool, author, status="changes_requested")
        published = await make_event(pool, author)
        await make_event(pool, await make_user(pool))
        async with uow() as tx:
            await tx.reactions.like(author.id, published.id, NOW)
            await tx.reactions.favorite(author.id, published.id, NOW)
            await tx.commit()
        async with uow() as tx:
            full = await tx.queries.authored(returned.id)
            mine = await tx.queries.by_author(author.id, None)
            only_returned = await tx.queries.by_author(author.id, EventStatus.CHANGES_REQUESTED)
        assert full is not None
        assert (full.author_name, full.moderator_note) == ("Иван", "Поправьте")
        assert {m.id for m in mine} == {returned.id, published.id}
        stats = next(m for m in mine if m.id == published.id)
        assert (stats.likes_count, stats.favorites_count) == (1, 1)
        assert [m.id for m in only_returned] == [returned.id]


class TestModerationQueue:
    async def test_oldest_first_and_resubmission_flag(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author = await make_user(pool)
        moderator = await make_user(pool, Role.MODERATOR)
        first = await make_event(pool, author, status="pending")
        second = await make_event(pool, author, status="pending")
        async with uow() as tx:
            e = await tx.events.get(second.id)
            assert e
            e.request_changes(note="Добавьте фото", now=NOW)
            await tx.events.update(e)
            e.submit(now=NOW + timedelta(minutes=1))
            await tx.events.update(e)
            await tx.commit()
        async with uow() as tx:
            queue = await tx.queries.moderation_queue(EventStatus.PENDING)
        assert [i.id for i in queue] == [first.id, second.id]
        assert [i.is_resubmission for i in queue] == [False, True]
        assert moderator.role.can_moderate


class TestCalendar:
    async def test_days_are_counted_in_university_timezone(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author = await make_user(pool)
        # 29 октября 23:30 по Уфе = 18:30 UTC; 30 октября 00:30 по Уфе = 19:30 UTC 29-го.
        base = datetime(2026, 10, 29, 18, 30, tzinfo=UTC) - NOW
        await make_event(
            pool, author, starts_in=base, title="Поздний квиз", category="entertainment"
        )
        await make_event(pool, author, starts_in=base + timedelta(minutes=1), title="Ещё одно")
        await make_event(pool, author, starts_in=base + timedelta(minutes=2), title="Третье")
        await make_event(pool, author, starts_in=base + timedelta(hours=1), title="Уже 30-е")
        await make_event(pool, author, status="pending", starts_in=base)
        async with uow() as tx:
            days = await tx.queries.calendar_month(2026, 10, UFA)
        assert [(d.day, d.count) for d in days] == [
            (date(2026, 10, 29), 3),
            (date(2026, 10, 30), 1),
        ]
        assert days[0].preview == [("Поздний квиз", "#0E7490"), ("Ещё одно", "#7C3AED")]

    async def test_category_counts(self, pool: asyncpg.Pool, uow: PostgresUnitOfWork) -> None:
        author = await make_user(pool)
        await make_event(pool, author, category="sport")
        await make_event(pool, author, category="sport", starts_in=-timedelta(days=3))
        async with uow() as tx:
            counts = {
                c.category.slug: c.upcoming_count for c in await tx.categories.list_with_counts(NOW)
            }
            assert (await tx.categories.get(1)) is not None
            assert await tx.categories.get(999) is None
        assert counts["sport"] == 1
        assert counts["concerts"] == 0
        assert len(counts) == 7
