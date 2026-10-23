import pytest

from studlenta.application.dto import ModerationAction, NotificationKind
from studlenta.application.use_cases.approve_event import ApproveEvent
from studlenta.application.use_cases.get_moderation_history import GetModerationHistory
from studlenta.application.use_cases.list_moderation_queue import ListModerationQueue
from studlenta.application.use_cases.reject_event import RejectEvent
from studlenta.application.use_cases.request_changes import RequestChanges
from studlenta.domain.errors import (
    ConflictError,
    InvalidTransitionError,
    PermissionDeniedError,
    ValidationError,
)
from studlenta.domain.events import EventStatus
from studlenta.domain.users import Role
from tests.fakes import FakeClock, FakeUnitOfWork, SequentialIds
from tests.unit.application.conftest import add_event, add_user


@pytest.fixture
async def setup(uow: FakeUnitOfWork):  # type: ignore[no-untyped-def]
    author = await add_user(uow, 1)
    moderator = await add_user(uow, 2, Role.MODERATOR)
    event = await add_event(uow, author, state="pending")
    return author, moderator, event


class TestApprove:
    async def test_publishes_logs_and_notifies_author(
        self, uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds, setup
    ) -> None:
        author, moderator, event = setup
        await ApproveEvent(uow, clock, ids)(moderator, event.id)

        assert uow.events.rows[event.id].status is EventStatus.PUBLISHED
        [entry] = uow.moderation_log.entries
        assert (entry.action, entry.actor_id) == (ModerationAction.APPROVED, moderator.user_id)
        [note] = uow.notifications.rows
        assert note.user_id == author.user_id
        assert note.kind is NotificationKind.APPROVED
        assert "опубликовано" in note.text

    async def test_authors_cannot_moderate(
        self, uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds, setup
    ) -> None:
        author, _, event = setup
        with pytest.raises(PermissionDeniedError):
            await ApproveEvent(uow, clock, ids)(author, event.id)

    async def test_moderator_cannot_approve_own_event(
        self, uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds, setup
    ) -> None:
        _, moderator, _ = setup
        own = await add_event(uow, moderator, n=2, state="pending")
        with pytest.raises(PermissionDeniedError, match="своё"):
            await ApproveEvent(uow, clock, ids)(moderator, own.id)

    async def test_second_moderator_gets_conflict(
        self, uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds, setup
    ) -> None:
        _, moderator, event = setup
        other = await add_user(uow, 3, Role.MODERATOR)
        stale = await uow.events.get(event.id)
        await ApproveEvent(uow, clock, ids)(moderator, event.id)
        assert stale is not None
        stale.reject(note="Поздно", now=clock.now())
        with pytest.raises(ConflictError):
            await uow.events.update(stale)
        with pytest.raises(InvalidTransitionError):
            await RejectEvent(uow, clock, ids)(other, event.id, "Поздно")


class TestReturnAndReject:
    async def test_request_changes_sends_note_to_author(
        self, uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds, setup
    ) -> None:
        _, moderator, event = setup
        await RequestChanges(uow, clock, ids)(moderator, event.id, "Укажите время окончания")
        stored = uow.events.rows[event.id]
        assert stored.status is EventStatus.CHANGES_REQUESTED
        assert stored.moderator_note == "Укажите время окончания"
        [note] = uow.notifications.rows
        assert note.kind is NotificationKind.CHANGES_REQUESTED
        assert "Укажите время окончания" in note.text

    async def test_reject_needs_reason(
        self, uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds, setup
    ) -> None:
        _, moderator, event = setup
        with pytest.raises(ValidationError):
            await RejectEvent(uow, clock, ids)(moderator, event.id, " ")
        assert uow.notifications.rows == []
        assert uow.events.rows[event.id].status is EventStatus.PENDING

    async def test_reject(
        self, uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds, setup
    ) -> None:
        _, moderator, event = setup
        await RejectEvent(uow, clock, ids)(moderator, event.id, "Реклама")
        assert uow.events.rows[event.id].status is EventStatus.REJECTED
        assert uow.notifications.rows[0].kind is NotificationKind.REJECTED


class TestQueueAndHistory:
    async def test_queue_defaults_to_pending(self, uow: FakeUnitOfWork, setup) -> None:
        _, moderator, _ = setup
        await ListModerationQueue(uow)(moderator)
        assert uow.queries.calls == [("moderation_queue", (EventStatus.PENDING,))]

    async def test_drafts_are_not_a_moderation_queue(self, uow: FakeUnitOfWork, setup) -> None:
        _, moderator, _ = setup
        with pytest.raises(ValidationError):
            await ListModerationQueue(uow)(moderator, EventStatus.DRAFT)

    async def test_queue_is_for_moderators(self, uow: FakeUnitOfWork, setup) -> None:
        author, _, _ = setup
        with pytest.raises(PermissionDeniedError):
            await ListModerationQueue(uow)(author)

    async def test_history_visible_to_author_and_moderators_only(
        self, uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds, setup
    ) -> None:
        author, moderator, event = setup
        await RequestChanges(uow, clock, ids)(moderator, event.id, "Добавьте фото")
        assert len(await GetModerationHistory(uow)(author, event.id)) == 1
        assert len(await GetModerationHistory(uow)(moderator, event.id)) == 1
        stranger = await add_user(uow, 9)
        with pytest.raises(PermissionDeniedError):
            await GetModerationHistory(uow)(stranger, event.id)
