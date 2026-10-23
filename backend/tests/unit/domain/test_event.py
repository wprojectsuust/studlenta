from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from studlenta.domain.errors import InvalidTransitionError, ValidationError
from studlenta.domain.events import Event, EventContent, EventStatus

NOW = datetime(2026, 10, 23, 7, 0, tzinfo=UTC)


def full_content(**overrides: object) -> EventContent:
    data: dict[str, object] = {
        "title": "Вечер студенческой музыки",
        "summary": "Живой звук и любимые хиты. Вход свободный.",
        "body": "Группа «Путь» и приглашённые гости — большой концерт в актовом зале.",
        "category_id": 1,
        "place": "Актовый зал УУНиТ",
        "starts_at": NOW + timedelta(days=2),
        "ends_at": NOW + timedelta(days=2, hours=3),
        "cover_url": None,
    }
    data.update(overrides)
    return EventContent(**data)  # type: ignore[arg-type]


def draft(**overrides: object) -> Event:
    return Event.create_draft(
        event_id=uuid4(), author_id=uuid4(), content=full_content(**overrides), now=NOW
    )


def pending() -> Event:
    event = draft()
    event.submit(now=NOW)
    return event


class TestCreateDraft:
    def test_new_event_is_a_draft_owned_by_author(self) -> None:
        author = uuid4()
        event = Event.create_draft(
            event_id=uuid4(), author_id=author, content=full_content(), now=NOW
        )
        assert event.status is EventStatus.DRAFT
        assert event.author_id == author
        assert event.created_at == NOW

    def test_draft_may_be_incomplete(self) -> None:
        event = draft(summary="", body="", place="", category_id=None, starts_at=None)
        assert event.status is EventStatus.DRAFT

    def test_draft_needs_a_title(self) -> None:
        with pytest.raises(ValidationError) as exc:
            draft(title="   ")
        assert "title" in exc.value.fields

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("title", "x" * 121),
            ("summary", "x" * 201),
            ("place", "x" * 201),
            ("body", "x" * 10_001),
        ],
    )
    def test_upper_limits_apply_even_to_drafts(self, field: str, value: str) -> None:
        with pytest.raises(ValidationError) as exc:
            draft(**{field: value})
        assert field in exc.value.fields

    def test_text_is_trimmed(self) -> None:
        event = draft(title="  Квиз  ", place=" Холл ")
        assert event.content.title == "Квиз"
        assert event.content.place == "Холл"


class TestSubmit:
    def test_complete_draft_goes_to_moderation(self) -> None:
        event = draft()
        event.submit(now=NOW)
        assert event.status is EventStatus.PENDING
        assert event.submitted_at == NOW

    def test_incomplete_draft_reports_every_missing_field(self) -> None:
        event = draft(
            title="Ква", summary="", body="коротко", place="", category_id=None, starts_at=None
        )
        with pytest.raises(ValidationError) as exc:
            event.submit(now=NOW)
        assert set(exc.value.fields) == {
            "title",
            "summary",
            "body",
            "place",
            "category_id",
            "starts_at",
        }
        assert event.status is EventStatus.DRAFT

    def test_event_in_the_past_cannot_be_submitted(self) -> None:
        event = draft(starts_at=NOW - timedelta(hours=1), ends_at=None)
        with pytest.raises(ValidationError) as exc:
            event.submit(now=NOW)
        assert "starts_at" in exc.value.fields

    def test_end_must_be_after_start(self) -> None:
        event = draft(ends_at=NOW + timedelta(days=1))
        with pytest.raises(ValidationError) as exc:
            event.submit(now=NOW)
        assert "ends_at" in exc.value.fields

    def test_resubmission_after_changes_requested_keeps_moderator_note(self) -> None:
        event = pending()
        event.request_changes(note="Укажите время окончания", now=NOW)
        event.submit(now=NOW)
        assert event.status is EventStatus.PENDING
        assert event.moderator_note == "Укажите время окончания"
        assert event.is_resubmission

    @pytest.mark.parametrize("status", [EventStatus.PENDING, EventStatus.PUBLISHED])
    def test_cannot_submit_twice(self, status: EventStatus) -> None:
        event = pending()
        if status is EventStatus.PUBLISHED:
            event.approve(now=NOW)
        with pytest.raises(InvalidTransitionError):
            event.submit(now=NOW)


class TestEdit:
    def test_draft_can_be_edited(self) -> None:
        event = draft()
        event.edit(full_content(title="Новый заголовок"), now=NOW + timedelta(minutes=1))
        assert event.content.title == "Новый заголовок"
        assert event.updated_at == NOW + timedelta(minutes=1)

    def test_returned_event_can_be_edited(self) -> None:
        event = pending()
        event.request_changes(note="Добавьте место", now=NOW)
        event.edit(full_content(place="Корпус А, ауд. 402"), now=NOW)
        assert event.content.place == "Корпус А, ауд. 402"

    @pytest.mark.parametrize("make", [pending, lambda: _published()])
    def test_event_under_review_or_published_is_frozen(self, make: object) -> None:
        event = make()  # type: ignore[operator]
        with pytest.raises(InvalidTransitionError):
            event.edit(full_content(), now=NOW)


def _published() -> Event:
    event = pending()
    event.approve(now=NOW)
    return event


class TestModeration:
    def test_approve_publishes_and_clears_note(self) -> None:
        event = pending()
        event.request_changes(note="Поправьте дату", now=NOW)
        event.submit(now=NOW)
        event.approve(now=NOW + timedelta(hours=1))
        assert event.status is EventStatus.PUBLISHED
        assert event.published_at == NOW + timedelta(hours=1)
        assert event.moderator_note is None
        assert event.is_visible_publicly

    @pytest.mark.parametrize("action", ["request_changes", "reject"])
    def test_return_and_reject_require_a_comment(self, action: str) -> None:
        event = pending()
        with pytest.raises(ValidationError) as exc:
            getattr(event, action)(note="  ", now=NOW)
        assert "note" in exc.value.fields
        assert event.status is EventStatus.PENDING

    def test_reject_is_final(self) -> None:
        event = pending()
        event.reject(note="Реклама", now=NOW)
        assert event.status is EventStatus.REJECTED
        with pytest.raises(InvalidTransitionError):
            event.submit(now=NOW)

    @pytest.mark.parametrize(
        "decide",
        [
            lambda e: e.approve(now=NOW),
            lambda e: e.request_changes(note="Комментарий", now=NOW),
            lambda e: e.reject(note="Комментарий", now=NOW),
        ],
    )
    def test_only_pending_events_are_moderated(self, decide: Callable[[Event], None]) -> None:
        event = draft()
        with pytest.raises(InvalidTransitionError):
            decide(event)


class TestWithdrawAndArchive:
    def test_author_can_withdraw_pending_back_to_draft(self) -> None:
        event = pending()
        event.withdraw(now=NOW)
        assert event.status is EventStatus.DRAFT
        assert event.submitted_at is None

    def test_published_event_can_be_archived(self) -> None:
        event = _published()
        event.archive(now=NOW)
        assert event.status is EventStatus.ARCHIVED
        assert not event.is_visible_publicly

    def test_draft_cannot_be_archived(self) -> None:
        with pytest.raises(InvalidTransitionError):
            draft().archive(now=NOW)

    def test_only_drafts_are_deletable(self) -> None:
        assert draft().is_deletable
        assert not pending().is_deletable
