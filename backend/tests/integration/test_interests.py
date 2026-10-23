from datetime import date, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import asyncpg
import pytest

from studlenta.domain.users import Role
from studlenta.infrastructure.db.uow import PostgresUnitOfWork
from tests.fakes import NOW
from tests.integration.conftest import make_event, make_user

pytestmark = pytest.mark.integration
UFA = ZoneInfo("Asia/Yekaterinburg")
DAY = date(2026, 10, 23)


def guest() -> str:
    return f"g:{uuid4()}"


async def view(uow: PostgresUnitOfWork, event_id: UUID, viewer: str, ago: timedelta) -> bool:
    at = NOW - ago
    async with uow() as tx:
        ok = await tx.interests.record_view(event_id, viewer, None, at.astimezone(UFA).date(), at)
        await tx.commit()
    return ok


class TestViews:
    async def test_one_view_per_viewer_per_day_and_only_published(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author = await make_user(pool)
        published = await make_event(pool, author)
        draft = await make_event(pool, author, status="draft")
        g = guest()
        assert await view(uow, published.id, g, timedelta(hours=1))
        assert await view(uow, published.id, g, timedelta(hours=1, minutes=5))
        assert not await view(uow, draft.id, g, timedelta(hours=1))
        assert await pool.fetchval("SELECT count(*) FROM event_views") == 1

    async def test_viewer_key_is_validated_by_the_database(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        event = await make_event(pool, await make_user(pool))
        with pytest.raises(asyncpg.CheckViolationError):
            await view(uow, event.id, "x:robert'); DROP TABLE events;--", timedelta(0))


class TestRecommendationInputs:
    async def test_history_merges_views_likes_and_favorites_with_lexemes(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author, me = await make_user(pool), await make_user(pool)
        jazz = await make_event(pool, author, title="Джазовый вечер", summary="Живая музыка")
        run = await make_event(pool, author, title="Осенний забег", category="sport")
        g = guest()
        await view(uow, jazz.id, g, timedelta(days=1))
        async with uow() as tx:
            await tx.reactions.favorite(me.id, run.id, NOW)
            await tx.commit()
        async with uow() as tx:
            items = await tx.interests.history([g, f"u:{me.id}"], me.id, NOW - timedelta(days=30))
        kinds = {(h.interaction.event_id, h.interaction.kind) for h in items}
        assert kinds == {(jazz.id, "view"), (run.id, "favorite")}
        jazz_item = next(h for h in items if h.interaction.event_id == jazz.id)
        assert jazz_item.title == "Джазовый вечер"
        assert "музык" in jazz_item.interaction.lexemes  # русская основа слова из tsvector

    async def test_candidates_are_upcoming_with_weighted_popularity(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author, fan = await make_user(pool), await make_user(pool)
        hot = await make_event(pool, author, starts_in=timedelta(days=3))
        calm = await make_event(pool, author, starts_in=timedelta(days=1))
        await make_event(pool, author, starts_in=-timedelta(days=1))
        await view(uow, hot.id, guest(), timedelta(hours=2))
        await view(uow, hot.id, guest(), timedelta(days=30))  # старый просмотр не в счёт
        async with uow() as tx:
            await tx.reactions.favorite(fan.id, hot.id, NOW)
            await tx.commit()
        async with uow() as tx:
            pool_ = await tx.interests.candidates(NOW, fan.id, NOW - timedelta(days=14), 50)
        assert [c.item.id for c in pool_] == [calm.id, hot.id]
        assert [c.popularity for c in pool_] == [0, 1 + 5]
        assert pool_[1].item.favorited

    async def test_co_views_count_other_people_only(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author = await make_user(pool)
        seed, other = await make_event(pool, author), await make_event(pool, author)
        me, a, b = guest(), guest(), guest()
        for v in (me, a, b):
            await view(uow, seed.id, v, timedelta(hours=1))
        for v in (me, a):
            await view(uow, other.id, v, timedelta(hours=1))
        async with uow() as tx:
            pairs = await tx.interests.co_views([seed.id], [me], NOW - timedelta(days=30))
        assert [(p.event_id, p.seed_id, p.viewers) for p in pairs] == [(other.id, seed.id, 1)]


class TestReport:
    async def test_totals_daily_series_categories_and_top(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author, fan = await make_user(pool), await make_user(pool)
        music = await make_event(pool, author, title="Концерт")
        sport = await make_event(pool, author, title="Футбол", category="sport")
        g1, g2 = guest(), guest()
        await view(uow, music.id, g1, timedelta(hours=1))
        await view(uow, music.id, g2, timedelta(hours=1))
        await view(uow, music.id, g1, timedelta(days=1))
        await view(uow, sport.id, g1, timedelta(days=2))
        async with uow() as tx:
            await tx.reactions.like(fan.id, music.id, NOW)
            await tx.reactions.favorite(fan.id, sport.id, NOW)
            await tx.commit()
        async with uow() as tx:
            report = await tx.interests.report(NOW - timedelta(days=7), NOW, UFA, None)
        assert report.scope == "all"
        assert (report.totals.views, report.totals.viewers) == (4, 2)
        assert (report.totals.likes, report.totals.favorites) == (1, 1)
        assert len(report.daily) == 8  # 7 суток назад … сегодня, включая пустые дни
        assert sum(d.views for d in report.daily) == 4
        assert report.daily[-1].day == DAY
        assert [c.category.slug for c in report.categories] == ["concerts", "sport"]
        assert report.top[0].id == music.id
        assert (report.top[0].views, report.top[0].viewers) == (3, 2)

    async def test_author_scope_hides_other_authors(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        me, other = await make_user(pool), await make_user(pool, Role.AUTHOR)
        mine = await make_event(pool, me)
        theirs = await make_event(pool, other)
        await view(uow, mine.id, guest(), timedelta(hours=1))
        await view(uow, theirs.id, guest(), timedelta(hours=1))
        async with uow() as tx:
            report = await tx.interests.report(NOW - timedelta(days=7), NOW, UFA, me.id)
        assert report.scope == "mine"
        assert report.totals.views == 1
        assert [e.id for e in report.top] == [mine.id]
