"""Модели чтения (read side). Их собирают SQL-запросы, а не доменные сущности."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from studlenta.domain.events import EventStatus
from studlenta.domain.users import Role


@dataclass(frozen=True, slots=True)
class Actor:
    """Тот, кто выполняет действие. Приходит из access-токена."""

    user_id: UUID
    role: Role


@dataclass(frozen=True, slots=True)
class CategoryRef:
    id: int
    slug: str
    name: str
    color: str


@dataclass(frozen=True, slots=True)
class CategoryWithCount:
    category: CategoryRef
    upcoming_count: int


@dataclass(frozen=True, slots=True)
class FeedItem:
    id: UUID
    title: str
    summary: str
    place: str
    starts_at: datetime
    ends_at: datetime | None
    cover_url: str | None
    category: CategoryRef
    likes_count: int
    liked: bool
    favorited: bool


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: list[T]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class EventDetails:
    item: FeedItem
    body: str
    organizer_name: str
    published_at: datetime


@dataclass(frozen=True, slots=True)
class MyEventItem:
    id: UUID
    title: str
    status: EventStatus
    cover_url: str | None
    starts_at: datetime | None
    updated_at: datetime
    moderator_note: str | None
    likes_count: int
    favorites_count: int


@dataclass(frozen=True, slots=True)
class AuthoredEvent:
    """Полная карточка для автора (форма редактирования) и модератора."""

    id: UUID
    author_id: UUID
    author_name: str
    status: EventStatus
    title: str
    summary: str
    body: str
    category: CategoryRef | None
    place: str
    starts_at: datetime | None
    ends_at: datetime | None
    cover_url: str | None
    moderator_note: str | None
    submitted_at: datetime | None
    updated_at: datetime
    is_resubmission: bool


class ModerationAction(StrEnum):
    SUBMITTED = "submitted"
    WITHDRAWN = "withdrawn"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class ModerationLogEntry:
    event_id: UUID
    actor_id: UUID
    action: ModerationAction
    note: str | None
    created_at: datetime
    actor_name: str = ""


@dataclass(frozen=True, slots=True)
class CalendarDay:
    day: date
    count: int
    preview: list[tuple[str, str]]  # (заголовок, цвет категории), не больше двух


class NotificationKind(StrEnum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"
    REMINDER = "reminder"


@dataclass(frozen=True, slots=True)
class Notification:
    id: UUID
    user_id: UUID
    kind: NotificationKind
    event_id: UUID
    text: str
    created_at: datetime
    read_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RefreshTokenRecord:
    token_hash: str
    user_id: UUID
    expires_at: datetime
    revoked_at: datetime | None


@dataclass(frozen=True, slots=True)
class Session:
    access_token: str
    refresh_token: str
    refresh_expires_at: datetime


@dataclass(frozen=True, slots=True)
class ImageInfo:
    format: str  # "jpeg" | "png" | "webp"
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class Profile:
    id: UUID
    email: str
    full_name: str
    role: Role
    unread_notifications: int


@dataclass(frozen=True, slots=True)
class Inbox:
    items: list[Notification]
    unread: int
