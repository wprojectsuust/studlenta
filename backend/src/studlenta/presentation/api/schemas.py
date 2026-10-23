"""HTTP-схемы. Pydantic проверяет только типы; бизнес-правила (длины, даты) — в домене,
чтобы сообщения об ошибках были одни и те же на любом входе.
"""

from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict

from studlenta.application import dto
from studlenta.domain.events import EventContent, EventStatus
from studlenta.domain.users import Role


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Запросы -----------------------------------------------------------------


class RegisterIn(_In):
    email: str
    password: str
    full_name: str


class LoginIn(_In):
    email: str
    password: str


class EventIn(_In):
    title: str
    summary: str = ""
    body: str = ""
    category_id: int | None = None
    place: str = ""
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    cover_url: str | None = None

    def to_content(self) -> EventContent:
        return EventContent(**self.model_dump())


class TokenIn(_In):
    token: str


class EmailIn(_In):
    email: str


class ResetPasswordIn(_In):
    token: str
    password: str


class SentOut(BaseModel):
    sent: bool


class NoteIn(_In):
    note: str


class SyncFavoritesIn(_In):
    event_ids: list[UUID]


class MarkReadIn(_In):
    ids: list[UUID] | None = None


# --- Ответы ------------------------------------------------------------------


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - тип токена по RFC 6750, не пароль
    expires_in: int


class CreatedOut(BaseModel):
    id: UUID


class UrlOut(BaseModel):
    url: str


class AddedOut(BaseModel):
    added: int


class CategoryOut(BaseModel):
    id: int
    slug: str
    name: str
    color: str

    @classmethod
    def of(cls, c: dto.CategoryRef) -> Self:
        return cls(id=c.id, slug=c.slug, name=c.name, color=c.color)


class CategoryCountOut(CategoryOut):
    upcoming_count: int


class FeedItemOut(BaseModel):
    id: UUID
    title: str
    summary: str
    place: str
    starts_at: datetime
    ends_at: datetime | None
    cover_url: str | None
    category: CategoryOut
    likes_count: int
    liked: bool
    favorited: bool

    @classmethod
    def of(cls, i: dto.FeedItem) -> Self:
        return cls(
            id=i.id, title=i.title, summary=i.summary, place=i.place, starts_at=i.starts_at,
            ends_at=i.ends_at, cover_url=i.cover_url, category=CategoryOut.of(i.category),
            likes_count=i.likes_count, liked=i.liked, favorited=i.favorited,
        )  # fmt: skip


class PageOut(BaseModel):
    items: list[FeedItemOut]
    next_cursor: str | None


class EventDetailsOut(FeedItemOut):
    body: str
    organizer_name: str
    published_at: datetime

    @classmethod
    def from_details(cls, d: dto.EventDetails) -> Self:
        return cls(
            **FeedItemOut.of(d.item).model_dump(),
            body=d.body, organizer_name=d.organizer_name, published_at=d.published_at,
        )  # fmt: skip


class MyEventOut(BaseModel):
    id: UUID
    title: str
    status: EventStatus
    cover_url: str | None
    starts_at: datetime | None
    updated_at: datetime
    moderator_note: str | None
    likes_count: int
    favorites_count: int


class AuthoredEventOut(BaseModel):
    id: UUID
    author_id: UUID
    author_name: str
    status: EventStatus
    title: str
    summary: str
    body: str
    category: CategoryOut | None
    place: str
    starts_at: datetime | None
    ends_at: datetime | None
    cover_url: str | None
    moderator_note: str | None
    submitted_at: datetime | None
    updated_at: datetime
    is_resubmission: bool

    @classmethod
    def of(cls, e: dto.AuthoredEvent) -> Self:
        data = {k: getattr(e, k) for k in cls.model_fields if k != "category"}
        return cls(**data, category=CategoryOut.of(e.category) if e.category else None)


class HistoryOut(BaseModel):
    action: dto.ModerationAction
    note: str | None
    created_at: datetime
    actor_name: str


class PreviewOut(BaseModel):
    title: str
    color: str


class CalendarDayOut(BaseModel):
    date: date
    count: int
    preview: list[PreviewOut]

    @classmethod
    def of(cls, d: dto.CalendarDay) -> Self:
        return cls(
            date=d.day, count=d.count, preview=[PreviewOut(title=t, color=c) for t, c in d.preview]
        )


class NotificationOut(BaseModel):
    id: UUID
    kind: dto.NotificationKind
    event_id: UUID
    text: str
    created_at: datetime
    read_at: datetime | None


class InboxOut(BaseModel):
    items: list[NotificationOut]
    unread: int


class ProfileOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: Role
    unread_notifications: int
    email_verified: bool


class ErrorBody(BaseModel):
    code: str
    message: str
    fields: dict[str, str] = {}


class ErrorOut(BaseModel):
    error: ErrorBody
