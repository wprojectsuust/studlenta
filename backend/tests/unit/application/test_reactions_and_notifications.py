from datetime import timedelta
from uuid import UUID

import pytest

from studlenta.application.dto import NotificationKind
from studlenta.application.use_cases.add_to_favorites import AddToFavorites
from studlenta.application.use_cases.approve_event import ApproveEvent
from studlenta.application.use_cases.like_event import LikeEvent
from studlenta.application.use_cases.list_notifications import ListNotifications
from studlenta.application.use_cases.mark_notifications_read import MarkNotificationsRead
from studlenta.application.use_cases.remove_from_favorites import RemoveFromFavorites
from studlenta.application.use_cases.send_favorite_reminders import SendFavoriteReminders
from studlenta.application.use_cases.sync_guest_favorites import MAX_SYNC, SyncGuestFavorites
from studlenta.application.use_cases.unlike_event import UnlikeEvent
from studlenta.domain.errors import NotFoundError, ValidationError
from studlenta.domain.users import Role
from tests.fakes import FakeClock, FakeUnitOfWork, SequentialIds
from tests.unit.application.conftest import add_event, add_user


class TestLikes:
    async def test_like_is_idempotent(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        user = await add_user(uow, 1)
        event = await add_event(uow, user, state="published")
        await LikeEvent(uow, clock)(user, event.id)
        await LikeEvent(uow, clock)(user, event.id)
        assert uow.reactions.likes == {(user.user_id, event.id)}
        await UnlikeEvent(uow)(user, event.id)
        assert uow.reactions.likes == set()

    async def test_cannot_like_unpublished(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        user = await add_user(uow, 1)
        event = await add_event(uow, user, state="pending")
        with pytest.raises(NotFoundError):
            await LikeEvent(uow, clock)(user, event.id)


class TestFavorites:
    async def test_add_and_remove(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        user = await add_user(uow, 1)
        event = await add_event(uow, user, state="published")
        await AddToFavorites(uow, clock)(user, event.id)
        assert (user.user_id, event.id) in uow.reactions.favorites
        await RemoveFromFavorites(uow)(user, event.id)
        assert uow.reactions.favorites == set()

    async def test_cannot_favorite_missing(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        user = await add_user(uow, 1)
        with pytest.raises(NotFoundError):
            await AddToFavorites(uow, clock)(user, UUID(int=404))

    async def test_guest_favorites_are_merged_skipping_unpublished(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        user = await add_user(uow, 1)
        good = await add_event(uow, user, n=1, state="published")
        hidden = await add_event(uow, user, n=2, state="pending")
        added = await SyncGuestFavorites(uow, clock)(user, [good.id, hidden.id, UUID(int=404)])
        assert added == 1
        assert uow.reactions.favorites == {(user.user_id, good.id)}

    async def test_sync_limit(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        user = await add_user(uow, 1)
        with pytest.raises(ValidationError):
            await SyncGuestFavorites(uow, clock)(user, [UUID(int=i) for i in range(MAX_SYNC + 1)])


class TestNotifications:
    async def test_inbox_with_unread_count_and_mark_read(
        self, uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds
    ) -> None:
        author, moderator = await add_user(uow, 1), await add_user(uow, 2, Role.MODERATOR)
        event = await add_event(uow, author, state="pending")
        await ApproveEvent(uow, clock, ids)(moderator, event.id)

        inbox = await ListNotifications(uow)(author)
        assert inbox.unread == 1
        assert [n.kind for n in inbox.items] == [NotificationKind.APPROVED]

        await MarkNotificationsRead(uow, clock)(author, ids=None)
        assert (await ListNotifications(uow)(author)).unread == 0

    async def test_reminder_once_for_favorites_starting_within_a_day(
        self, uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds
    ) -> None:
        user = await add_user(uow, 1)
        soon = await add_event(uow, user, n=1, state="published")  # через 2 дня
        await AddToFavorites(uow, clock)(user, soon.id)
        remind = SendFavoriteReminders(uow, clock, ids)

        assert await remind() == 0
        clock.advance(days=1, hours=1)
        assert await remind() == 1
        assert await remind() == 0  # не дублируем
        [note] = uow.notifications.rows
        assert note.kind is NotificationKind.REMINDER
        assert "завтра" in note.text or "скоро" in note.text
        assert note.created_at == clock.now()
        assert soon.content.starts_at is not None
        assert soon.content.starts_at - clock.now() < timedelta(days=1)
