from uuid import UUID

import pytest

from studlenta.application.dto import ImageInfo, ModerationAction
from studlenta.application.use_cases.archive_event import ArchiveEvent
from studlenta.application.use_cases.create_draft import CreateDraft
from studlenta.application.use_cases.delete_draft import DeleteDraft
from studlenta.application.use_cases.get_event_for_editing import GetEventForEditing
from studlenta.application.use_cases.list_my_events import ListMyEvents
from studlenta.application.use_cases.submit_for_moderation import SubmitForModeration
from studlenta.application.use_cases.update_draft import UpdateDraft
from studlenta.application.use_cases.upload_cover import MAX_COVER_BYTES, UploadCover
from studlenta.application.use_cases.withdraw_submission import WithdrawSubmission
from studlenta.domain.errors import (
    InvalidTransitionError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from studlenta.domain.events import EventStatus
from studlenta.domain.users import Role
from tests.fakes import FakeClock, FakeImageInspector, FakeStorage, FakeUnitOfWork, SequentialIds
from tests.unit.application.conftest import add_event, add_user, authored, content


class TestCreateDraft:
    async def test_saves_draft_for_actor(
        self, uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds
    ) -> None:
        author = await add_user(uow, 1)
        event_id = await CreateDraft(uow, clock, ids)(author, content(title="Квиз"))
        stored = uow.events.rows[event_id]
        assert stored.status is EventStatus.DRAFT
        assert stored.author_id == author.user_id
        assert uow.commits == 1

    async def test_unknown_category_is_a_field_error(
        self, uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds
    ) -> None:
        author = await add_user(uow, 1)
        with pytest.raises(ValidationError) as exc:
            await CreateDraft(uow, clock, ids)(author, content(category_id=99))
        assert "category_id" in exc.value.fields
        assert uow.events.rows == {}


class TestUpdateDraft:
    async def test_author_edits_own_draft(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        author = await add_user(uow, 1)
        event = await add_event(uow, author)
        clock.advance(minutes=5)
        await UpdateDraft(uow, clock)(author, event.id, content(place="Корпус А"))
        assert uow.events.rows[event.id].content.place == "Корпус А"
        assert uow.events.rows[event.id].updated_at == clock.now()

    async def test_someone_else_cannot_edit(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        author, stranger = await add_user(uow, 1), await add_user(uow, 2)
        event = await add_event(uow, author)
        with pytest.raises(PermissionDeniedError):
            await UpdateDraft(uow, clock)(stranger, event.id, content())

    async def test_missing_event(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        author = await add_user(uow, 1)
        with pytest.raises(NotFoundError):
            await UpdateDraft(uow, clock)(author, UUID(int=1), content())


class TestSubmit:
    async def test_goes_to_queue_and_is_logged(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        author = await add_user(uow, 1)
        event = await add_event(uow, author)
        await SubmitForModeration(uow, clock)(author, event.id)
        assert uow.events.rows[event.id].status is EventStatus.PENDING
        [entry] = uow.moderation_log.entries
        assert entry.action is ModerationAction.SUBMITTED
        assert entry.actor_id == author.user_id

    async def test_validation_errors_roll_back(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        author = await add_user(uow, 1)
        event = await add_event(uow, author)
        await UpdateDraft(uow, clock)(author, event.id, content(summary=""))
        with pytest.raises(ValidationError):
            await SubmitForModeration(uow, clock)(author, event.id)
        assert uow.moderation_log.entries == []


class TestWithdraw:
    async def test_back_to_draft(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        author = await add_user(uow, 1)
        event = await add_event(uow, author, state="pending")
        await WithdrawSubmission(uow, clock)(author, event.id)
        assert uow.events.rows[event.id].status is EventStatus.DRAFT
        assert uow.moderation_log.entries[-1].action is ModerationAction.WITHDRAWN


class TestArchive:
    async def test_author_archives_published(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        author = await add_user(uow, 1)
        event = await add_event(uow, author, state="published")
        await ArchiveEvent(uow, clock)(author, event.id)
        assert uow.events.rows[event.id].status is EventStatus.ARCHIVED

    async def test_moderator_may_archive_anyones(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        author, moderator = await add_user(uow, 1), await add_user(uow, 2, Role.MODERATOR)
        event = await add_event(uow, author, state="published")
        await ArchiveEvent(uow, clock)(moderator, event.id)
        assert uow.events.rows[event.id].status is EventStatus.ARCHIVED

    async def test_stranger_may_not(self, uow: FakeUnitOfWork, clock: FakeClock) -> None:
        author, stranger = await add_user(uow, 1), await add_user(uow, 2)
        event = await add_event(uow, author, state="published")
        with pytest.raises(PermissionDeniedError):
            await ArchiveEvent(uow, clock)(stranger, event.id)


class TestDeleteDraft:
    async def test_draft_is_removed(self, uow: FakeUnitOfWork) -> None:
        author = await add_user(uow, 1)
        event = await add_event(uow, author)
        await DeleteDraft(uow)(author, event.id)
        assert event.id not in uow.events.rows

    async def test_submitted_event_stays(self, uow: FakeUnitOfWork) -> None:
        author = await add_user(uow, 1)
        event = await add_event(uow, author, state="pending")
        with pytest.raises(InvalidTransitionError):
            await DeleteDraft(uow)(author, event.id)


class TestReadOwnEvents:
    async def test_list_passes_actor_and_status(self, uow: FakeUnitOfWork) -> None:
        author = await add_user(uow, 1)
        await ListMyEvents(uow)(author, EventStatus.PENDING)
        assert uow.queries.calls == [("by_author", (author.user_id, EventStatus.PENDING))]

    async def test_editing_view_hidden_from_strangers(self, uow: FakeUnitOfWork) -> None:
        author, stranger = await add_user(uow, 1), await add_user(uow, 2)
        uow.queries.authored_result = authored(author_id=author.user_id)
        assert await GetEventForEditing(uow)(author, uow.queries.authored_result.id)
        with pytest.raises(PermissionDeniedError):
            await GetEventForEditing(uow)(stranger, uow.queries.authored_result.id)

    async def test_editing_view_missing(self, uow: FakeUnitOfWork) -> None:
        author = await add_user(uow, 1)
        with pytest.raises(NotFoundError):
            await GetEventForEditing(uow)(author, author.user_id)


class TestUploadCover:
    @pytest.fixture
    def storage(self) -> FakeStorage:
        return FakeStorage()

    async def test_stores_image_under_generated_name(
        self, uow: FakeUnitOfWork, ids: SequentialIds, storage: FakeStorage
    ) -> None:
        author = await add_user(uow, 1)
        url = await UploadCover(storage, FakeImageInspector(), ids)(author, b"jpegdata")
        assert url == "/media/covers/00000000-0000-0000-0000-000000000001.jpg"
        assert storage.files["covers/00000000-0000-0000-0000-000000000001.jpg"] == b"jpegdata"

    @pytest.mark.parametrize(
        ("info", "size", "message"),
        [
            (None, 10, "JPG, PNG или WEBP"),
            (ImageInfo("gif", 1600, 900), 10, "JPG, PNG или WEBP"),
            (ImageInfo("png", 800, 600), 10, "1200"),
            (ImageInfo("png", 1600, 900), MAX_COVER_BYTES + 1, "5 МБ"),
        ],
    )
    async def test_rejects_bad_files(
        self,
        uow: FakeUnitOfWork,
        ids: SequentialIds,
        storage: FakeStorage,
        info: ImageInfo | None,
        size: int,
        message: str,
    ) -> None:
        author = await add_user(uow, 1)
        with pytest.raises(ValidationError) as exc:
            await UploadCover(storage, FakeImageInspector(info), ids)(author, b"x" * size)
        assert message in exc.value.fields["cover"]
        assert storage.files == {}
