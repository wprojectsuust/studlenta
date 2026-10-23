"""Событие и его жизненный цикл с предмодерацией.

    draft ──submit──▶ pending ──approve──────────▶ published ──archive──▶ archived
      ▲                │  │  └─request_changes─▶ changes_requested ──submit──▶ pending
      └───withdraw─────┘  └─reject──▶ rejected

Все переходы проверяются здесь, а не в SQL и не в роутерах: так правила покрыты
юнит-тестами без базы данных.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from studlenta.domain.errors import InvalidTransitionError, ValidationError

TITLE_MIN, TITLE_MAX = 5, 120
SUMMARY_MAX = 200
BODY_MIN, BODY_MAX = 20, 10_000
PLACE_MIN, PLACE_MAX = 3, 200
NOTE_MAX = 1_000


class EventStatus(StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    CHANGES_REQUESTED = "changes_requested"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


EDITABLE = frozenset({EventStatus.DRAFT, EventStatus.CHANGES_REQUESTED})


@dataclass(frozen=True, slots=True)
class EventContent:
    """То, что пишет автор. В черновике почти всё может быть пустым."""

    title: str
    summary: str = ""
    body: str = ""
    category_id: int | None = None
    place: str = ""
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    cover_url: str | None = None

    def normalized(self) -> "EventContent":
        return replace(
            self,
            title=self.title.strip(),
            summary=self.summary.strip(),
            body=self.body.strip(),
            place=self.place.strip(),
        )

    def draft_errors(self) -> dict[str, str]:
        errors: dict[str, str] = {}
        if not self.title:
            errors["title"] = "Укажите заголовок"
        elif len(self.title) > TITLE_MAX:
            errors["title"] = f"Заголовок — не длиннее {TITLE_MAX} символов"
        if len(self.summary) > SUMMARY_MAX:
            errors["summary"] = f"Анонс — не длиннее {SUMMARY_MAX} символов"
        if len(self.body) > BODY_MAX:
            errors["body"] = f"Описание — не длиннее {BODY_MAX} символов"
        if len(self.place) > PLACE_MAX:
            errors["place"] = f"Место — не длиннее {PLACE_MAX} символов"
        return errors

    def submit_errors(self, now: datetime) -> dict[str, str]:
        errors = self.draft_errors()
        if "title" not in errors and len(self.title) < TITLE_MIN:
            errors["title"] = f"Заголовок — минимум {TITLE_MIN} символов"
        if not self.summary:
            errors["summary"] = "Добавьте краткий анонс"
        if "body" not in errors and len(self.body) < BODY_MIN:
            errors["body"] = "Опишите событие подробнее"
        if "place" not in errors and len(self.place) < PLACE_MIN:
            errors["place"] = "Укажите место проведения"
        if self.category_id is None:
            errors["category_id"] = "Выберите категорию"
        if self.starts_at is None:
            errors["starts_at"] = "Укажите дату и время"
        elif self.starts_at <= now:
            errors["starts_at"] = "Дата уже прошла"
        elif self.ends_at is not None and self.ends_at <= self.starts_at:
            errors["ends_at"] = "Окончание должно быть позже начала"
        return errors


def _require_note(note: str) -> str:
    note = note.strip()
    if not note:
        raise ValidationError({"note": "Напишите автору, что не так"})
    if len(note) > NOTE_MAX:
        raise ValidationError({"note": f"Комментарий — не длиннее {NOTE_MAX} символов"})
    return note


@dataclass(slots=True)
class Event:
    id: UUID
    author_id: UUID
    content: EventContent
    status: EventStatus
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None
    published_at: datetime | None = None
    moderator_note: str | None = None
    version: int = 1

    @classmethod
    def create_draft(
        cls, *, event_id: UUID, author_id: UUID, content: EventContent, now: datetime
    ) -> "Event":
        content = content.normalized()
        if errors := content.draft_errors():
            raise ValidationError(errors)
        return cls(
            id=event_id,
            author_id=author_id,
            content=content,
            status=EventStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )

    @property
    def is_visible_publicly(self) -> bool:
        return self.status is EventStatus.PUBLISHED

    @property
    def is_deletable(self) -> bool:
        return self.status is EventStatus.DRAFT

    @property
    def is_resubmission(self) -> bool:
        """Автор исправил заявку после возврата — модератор видит пометку."""
        return self.status is EventStatus.PENDING and self.moderator_note is not None

    def _ensure(self, allowed: frozenset[EventStatus] | EventStatus, action: str) -> None:
        ok = self.status in allowed if isinstance(allowed, frozenset) else self.status is allowed
        if not ok:
            raise InvalidTransitionError(self.status.value, action)

    def edit(self, content: EventContent, *, now: datetime) -> None:
        self._ensure(EDITABLE, "edit")
        content = content.normalized()
        if errors := content.draft_errors():
            raise ValidationError(errors)
        self.content = content
        self.updated_at = now

    def submit(self, *, now: datetime) -> None:
        self._ensure(EDITABLE, "submit")
        if errors := self.content.submit_errors(now):
            raise ValidationError(errors)
        self.status = EventStatus.PENDING
        self.submitted_at = now
        self.updated_at = now

    def withdraw(self, *, now: datetime) -> None:
        self._ensure(EventStatus.PENDING, "withdraw")
        self.status = EventStatus.DRAFT
        self.submitted_at = None
        self.updated_at = now

    def approve(self, *, now: datetime) -> None:
        self._ensure(EventStatus.PENDING, "approve")
        self.status = EventStatus.PUBLISHED
        self.published_at = now
        self.moderator_note = None
        self.updated_at = now

    def request_changes(self, *, note: str, now: datetime) -> None:
        self._ensure(EventStatus.PENDING, "request_changes")
        self.moderator_note = _require_note(note)
        self.status = EventStatus.CHANGES_REQUESTED
        self.updated_at = now

    def reject(self, *, note: str, now: datetime) -> None:
        self._ensure(EventStatus.PENDING, "reject")
        self.moderator_note = _require_note(note)
        self.status = EventStatus.REJECTED
        self.updated_at = now

    def archive(self, *, now: datetime) -> None:
        self._ensure(EventStatus.PUBLISHED, "archive")
        self.status = EventStatus.ARCHIVED
        self.updated_at = now
