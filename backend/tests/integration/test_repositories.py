from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import asyncpg
import pytest

from studlenta.application.dto import (
    EmailVerificationRecord,
    ModerationAction,
    ModerationLogEntry,
    Notification,
    NotificationKind,
    RefreshTokenRecord,
)
from studlenta.domain.errors import ConflictError
from studlenta.domain.events import EventContent, EventStatus
from studlenta.domain.users import Role, User
from studlenta.infrastructure.db.migrate import apply_migrations
from studlenta.infrastructure.db.uow import PostgresUnitOfWork
from tests.fakes import NOW
from tests.integration.conftest import make_event, make_user

pytestmark = pytest.mark.integration


class TestMigrations:
    async def test_rerun_is_noop_and_categories_are_seeded(
        self, pool: asyncpg.Pool, database_url: str
    ) -> None:
        assert await apply_migrations(database_url) == []
        rows = await pool.fetch("SELECT slug FROM categories ORDER BY position")
        slugs = [r["slug"] for r in rows]
        assert slugs == [
            "concerts",
            "sport",
            "science",
            "volunteering",
            "culture",
            "entertainment",
            "other",
        ]


class TestUnitOfWork:
    async def test_without_commit_nothing_is_saved(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        user = User(uuid4(), "rollback@uust.ru", "Анна", Role.AUTHOR, "hash", NOW)
        async with uow() as tx:
            await tx.users.add(user)
        async with uow() as tx:
            assert await tx.users.get(user.id) is None

    async def test_exception_rolls_back(self, uow: PostgresUnitOfWork) -> None:
        user = User(uuid4(), "boom@uust.ru", "Анна", Role.AUTHOR, "hash", NOW)

        async def fail_midway() -> None:
            async with uow() as tx:
                await tx.users.add(user)
                raise RuntimeError

        with pytest.raises(RuntimeError):
            await fail_midway()
        async with uow() as tx:
            assert await tx.users.get_by_email("boom@uust.ru") is None


class TestUsers:
    async def test_roundtrip_and_duplicate_email(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        user = await make_user(pool, Role.MODERATOR)
        async with uow() as tx:
            assert await tx.users.get(user.id) == user
            assert await tx.users.get_by_email(user.email) == user
            with pytest.raises(ConflictError):
                await tx.users.add(replace(user, id=uuid4()))


class TestEvents:
    async def test_roundtrip_keeps_every_field(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author = await make_user(pool)
        event = await make_event(pool, author, status="changes_requested")
        async with uow() as tx:
            loaded = await tx.events.get(event.id)
        assert loaded == event

    async def test_draft_without_category_and_date(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        from studlenta.domain.events import Event

        author = await make_user(pool)
        event = Event.create_draft(
            event_id=uuid4(), author_id=author.id, content=EventContent(title="Идея"), now=NOW
        )
        async with uow() as tx:
            await tx.events.add(event)
            await tx.commit()
        async with uow() as tx:
            assert await tx.events.get(event.id) == event

    async def test_update_bumps_version_and_detects_races(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        moderator = await make_user(pool, Role.MODERATOR)
        event = await make_event(pool, await make_user(pool), status="pending")
        async with uow() as first, uow() as second:
            a = await first.events.get(event.id)
            b = await second.events.get(event.id)
            assert a
            assert b
            a.approve(now=NOW)
            await first.events.update(a)
            await first.commit()
            assert a.version == 2
            b.reject(note="Поздно", now=NOW)
            with pytest.raises(ConflictError):
                await second.events.update(b)
        assert moderator.role is Role.MODERATOR
        async with uow() as tx:
            stored = await tx.events.get(event.id)
        assert stored
        assert stored.status is EventStatus.PUBLISHED

    async def test_delete(self, pool: asyncpg.Pool, uow: PostgresUnitOfWork) -> None:
        event = await make_event(pool, await make_user(pool), status="draft")
        async with uow() as tx:
            await tx.events.delete(event.id)
            await tx.commit()
        async with uow() as tx:
            assert await tx.events.get(event.id) is None


class TestReactions:
    async def test_likes_and_favorites_are_idempotent(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        user = await make_user(pool)
        event = await make_event(pool, user)
        async with uow() as tx:
            for _ in range(2):
                await tx.reactions.like(user.id, event.id, NOW)
                await tx.reactions.favorite(user.id, event.id, NOW)
            await tx.commit()
        assert await pool.fetchval("SELECT count(*) FROM likes") == 1
        async with uow() as tx:
            await tx.reactions.unlike(user.id, event.id)
            await tx.reactions.unfavorite(user.id, event.id)
            await tx.reactions.unfavorite(user.id, event.id)
            await tx.commit()
        assert await pool.fetchval("SELECT count(*) FROM likes") == 0
        assert await pool.fetchval("SELECT count(*) FROM favorites") == 0

    async def test_published_ids_and_reminder_window(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        user = await make_user(pool)
        soon = await make_event(pool, user, starts_in=timedelta(hours=10), title="Скоро")
        later = await make_event(pool, user, starts_in=timedelta(days=3))
        hidden = await make_event(pool, user, status="pending")
        async with uow() as tx:
            assert await tx.reactions.published_ids([soon.id, later.id, hidden.id]) == {
                soon.id,
                later.id,
            }
            for e in (soon, later):
                await tx.reactions.favorite(user.id, e.id, NOW)
            window = await tx.reactions.favorites_starting_between(NOW, NOW + timedelta(days=1))
        assert window == [(user.id, soon.id, "Скоро")]


class TestModerationLogAndNotifications:
    async def test_log_newest_first_with_actor_name(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        author = await make_user(pool, name="Иван Петров")
        moderator = await make_user(pool, Role.MODERATOR, name="Елена Орлова")
        event = await make_event(pool, author, status="pending")
        async with uow() as tx:
            await tx.moderation_log.add(
                ModerationLogEntry(event.id, author.id, ModerationAction.SUBMITTED, None, NOW)
            )
            await tx.moderation_log.add(
                ModerationLogEntry(
                    event.id,
                    moderator.id,
                    ModerationAction.CHANGES_REQUESTED,
                    "Фото",
                    NOW + timedelta(minutes=5),
                )
            )
            await tx.commit()
        async with uow() as tx:
            log = await tx.moderation_log.list_for_event(event.id)
        assert [(e.action, e.actor_name, e.note) for e in log] == [
            (ModerationAction.CHANGES_REQUESTED, "Елена Орлова", "Фото"),
            (ModerationAction.SUBMITTED, "Иван Петров", None),
        ]

    async def test_reminders_deduplicated_and_read_marks(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        user = await make_user(pool)
        event = await make_event(pool, user)

        def note(kind: NotificationKind, minutes: int) -> Notification:
            return Notification(
                uuid4(), user.id, kind, event.id, "текст", NOW + timedelta(minutes=minutes)
            )

        async with uow() as tx:
            assert await tx.notifications.add(note(NotificationKind.REMINDER, 0))
            assert not await tx.notifications.add(note(NotificationKind.REMINDER, 1))
            approved = note(NotificationKind.APPROVED, 2)
            assert await tx.notifications.add(approved)
            assert await tx.notifications.add(note(NotificationKind.APPROVED, 3))
            await tx.commit()
        async with uow() as tx:
            items = await tx.notifications.list_for_user(user.id, 10, None)
            assert [n.created_at for n in items] == [NOW + timedelta(minutes=m) for m in (3, 2, 0)]
            older = await tx.notifications.list_for_user(user.id, 10, NOW + timedelta(minutes=2))
            assert len(older) == 1
            await tx.notifications.mark_read(user.id, [approved.id], NOW)
            assert await tx.notifications.count_unread(user.id) == 2
            await tx.notifications.mark_read(user.id, None, NOW)
            assert await tx.notifications.count_unread(user.id) == 0
            await tx.commit()


class TestRefreshTokens:
    async def test_add_get_revoke(self, pool: asyncpg.Pool, uow: PostgresUnitOfWork) -> None:
        user = await make_user(pool)
        record = RefreshTokenRecord("abc", user.id, NOW + timedelta(days=30), None)
        async with uow() as tx:
            await tx.refresh_tokens.add(record)
            assert await tx.refresh_tokens.get("abc") == record
            await tx.refresh_tokens.revoke("abc", NOW)
            stored = await tx.refresh_tokens.get("abc")
            assert stored
            assert stored.revoked_at == NOW
            assert await tx.refresh_tokens.get("missing") is None


class TestEmailVerifications:
    async def test_tokens_and_marking_user_verified(
        self, pool: asyncpg.Pool, uow: PostgresUnitOfWork
    ) -> None:
        user = await make_user(pool)
        assert user.email_verified_at is None
        first = EmailVerificationRecord("h1", user.id, NOW, NOW + timedelta(days=1))
        second = EmailVerificationRecord(
            "h2", user.id, NOW + timedelta(minutes=5), NOW + timedelta(days=1)
        )
        async with uow() as tx:
            assert await tx.email_verifications.latest_created_at(user.id) is None
            await tx.email_verifications.add(first)
            await tx.email_verifications.add(second)
            assert await tx.email_verifications.get("h1") == first
            assert await tx.email_verifications.get("nope") is None
            latest = await tx.email_verifications.latest_created_at(user.id)
            assert latest == NOW + timedelta(minutes=5)
            await tx.users.mark_email_verified(user.id, NOW)
            await tx.commit()
        async with uow() as tx:
            stored = await tx.users.get(user.id)
        assert stored is not None
        assert stored.email_verified_at == NOW
        assert stored.is_verified
