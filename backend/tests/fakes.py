"""In-memory реализации портов для юнит-тестов use case'ов.

Логику SQL-запросов (EventQueries) здесь не повторяем — её проверяют интеграционные тесты.
Вместо неё ``StubQueries`` запоминает аргументы и возвращает заготовленные ответы.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta, tzinfo
from types import TracebackType
from typing import Any, Self
from uuid import UUID

from studlenta.application.dto import (
    AuthoredEvent,
    CalendarDay,
    CategoryRef,
    CategoryWithCount,
    EmailMessage,
    EmailVerificationRecord,
    EventDetails,
    FeedItem,
    ImageInfo,
    ModerationLogEntry,
    MyEventItem,
    Notification,
    RefreshTokenRecord,
)
from studlenta.application.ports import FeedQuery
from studlenta.domain.categories import Category
from studlenta.domain.errors import ConflictError
from studlenta.domain.events import Event, EventStatus
from studlenta.domain.users import User

NOW = datetime(2026, 10, 23, 7, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, now: datetime = NOW) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current += timedelta(**delta)


class SequentialIds:
    def __init__(self) -> None:
        self.counter = 0

    def new_id(self) -> UUID:
        self.counter += 1
        return UUID(int=self.counter)


class FakeHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password_hash: str, password: str) -> bool:
        return password_hash == f"hashed:{password}"


class FakeTokens:
    def __init__(self) -> None:
        self.counter = 0

    def issue_access_token(self, user: User, now: datetime) -> str:
        return f"access:{user.id}:{user.role}"

    def new_refresh_token(self) -> str:
        self.counter += 1
        return f"refresh-{self.counter}"

    def hash_refresh_token(self, token: str) -> str:
        return f"h({token})"


class FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def save(self, name: str, data: bytes) -> str:
        self.files[name] = data
        return f"/media/{name}"


DEFAULT_IMAGE = ImageInfo("jpeg", 1600, 900)


class FakeImageInspector:
    def __init__(self, info: ImageInfo | None = DEFAULT_IMAGE) -> None:
        self.info = info

    def inspect(self, data: bytes) -> ImageInfo | None:
        return self.info


class InMemoryEvents:
    def __init__(self) -> None:
        self.rows: dict[UUID, Event] = {}

    async def get(self, event_id: UUID) -> Event | None:
        event = self.rows.get(event_id)
        return replace(event) if event else None

    async def add(self, event: Event) -> None:
        self.rows[event.id] = replace(event)

    async def update(self, event: Event) -> None:
        stored = self.rows[event.id]
        if stored.version != event.version:
            raise ConflictError("Событие уже изменено")
        event.version += 1
        self.rows[event.id] = replace(event)

    async def delete(self, event_id: UUID) -> None:
        self.rows.pop(event_id, None)


class InMemoryUsers:
    def __init__(self) -> None:
        self.rows: dict[UUID, User] = {}

    async def get(self, user_id: UUID) -> User | None:
        return self.rows.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.rows.values() if u.email == email), None)

    async def add(self, user: User) -> None:
        if await self.get_by_email(user.email):
            raise ConflictError("Почта уже зарегистрирована")
        self.rows[user.id] = user

    async def mark_email_verified(self, user_id: UUID, now: datetime) -> None:
        self.rows[user_id] = replace(self.rows[user_id], email_verified_at=now)


class InMemoryEmailVerifications:
    def __init__(self) -> None:
        self.rows: dict[str, EmailVerificationRecord] = {}

    async def add(self, record: EmailVerificationRecord) -> None:
        self.rows[record.token_hash] = record

    async def get(self, token_hash: str) -> EmailVerificationRecord | None:
        return self.rows.get(token_hash)

    async def latest_created_at(self, user_id: UUID) -> datetime | None:
        return max((r.created_at for r in self.rows.values() if r.user_id == user_id), default=None)


class FakeMailer:
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []
        self.fail = False

    async def send(self, message: EmailMessage) -> None:
        if self.fail:
            raise OSError("SMTP недоступен")
        self.sent.append(message)


class InMemoryCategories:
    def __init__(self) -> None:
        self.rows: dict[int, Category] = {
            1: Category(1, "concerts", "Концерты", "#7C3AED"),
            2: Category(2, "sport", "Спорт", "#15803D"),
        }
        self.counts: list[CategoryWithCount] = []
        self.calls: list[datetime] = []

    async def get(self, category_id: int) -> Category | None:
        return self.rows.get(category_id)

    async def list_with_counts(self, upcoming_from: datetime) -> list[CategoryWithCount]:
        self.calls.append(upcoming_from)
        return self.counts


class InMemoryReactions:
    def __init__(self, events: InMemoryEvents) -> None:
        self.events = events
        self.likes: set[tuple[UUID, UUID]] = set()
        self.favorites: set[tuple[UUID, UUID]] = set()

    async def like(self, user_id: UUID, event_id: UUID, now: datetime) -> None:
        self.likes.add((user_id, event_id))

    async def unlike(self, user_id: UUID, event_id: UUID) -> None:
        self.likes.discard((user_id, event_id))

    async def favorite(self, user_id: UUID, event_id: UUID, now: datetime) -> None:
        self.favorites.add((user_id, event_id))

    async def unfavorite(self, user_id: UUID, event_id: UUID) -> None:
        self.favorites.discard((user_id, event_id))

    async def published_ids(self, event_ids: Sequence[UUID]) -> set[UUID]:
        return {
            i
            for i in event_ids
            if (e := self.events.rows.get(i)) and e.status is EventStatus.PUBLISHED
        }

    async def favorites_starting_between(
        self, start: datetime, end: datetime
    ) -> list[tuple[UUID, UUID, str]]:
        out = []
        for user_id, event_id in sorted(self.favorites):
            e = self.events.rows.get(event_id)
            if (
                e
                and e.status is EventStatus.PUBLISHED
                and e.content.starts_at
                and start <= e.content.starts_at < end
            ):
                out.append((user_id, event_id, e.content.title))
        return out


class InMemoryModerationLog:
    def __init__(self) -> None:
        self.entries: list[ModerationLogEntry] = []

    async def add(self, entry: ModerationLogEntry) -> None:
        self.entries.append(entry)

    async def list_for_event(self, event_id: UUID) -> list[ModerationLogEntry]:
        return sorted(
            (e for e in self.entries if e.event_id == event_id),
            key=lambda e: e.created_at,
            reverse=True,
        )


class InMemoryNotifications:
    def __init__(self) -> None:
        self.rows: list[Notification] = []

    async def add(self, notification: Notification) -> bool:
        if notification.kind == "reminder" and any(
            n.user_id == notification.user_id
            and n.event_id == notification.event_id
            and n.kind == notification.kind
            for n in self.rows
        ):
            return False
        self.rows.append(notification)
        return True

    async def list_for_user(
        self, user_id: UUID, limit: int, before: datetime | None
    ) -> list[Notification]:
        mine = [
            n
            for n in self.rows
            if n.user_id == user_id and (before is None or n.created_at < before)
        ]
        return sorted(mine, key=lambda n: n.created_at, reverse=True)[:limit]

    async def count_unread(self, user_id: UUID) -> int:
        return sum(1 for n in self.rows if n.user_id == user_id and n.read_at is None)

    async def mark_read(self, user_id: UUID, ids: Sequence[UUID] | None, now: datetime) -> None:
        self.rows = [
            replace(n, read_at=now)
            if n.user_id == user_id and n.read_at is None and (ids is None or n.id in ids)
            else n
            for n in self.rows
        ]


class InMemoryRefreshTokens:
    def __init__(self) -> None:
        self.rows: dict[str, RefreshTokenRecord] = {}

    async def add(self, record: RefreshTokenRecord) -> None:
        self.rows[record.token_hash] = record

    async def get(self, token_hash: str) -> RefreshTokenRecord | None:
        return self.rows.get(token_hash)

    async def revoke(self, token_hash: str, now: datetime) -> None:
        if token_hash in self.rows:
            self.rows[token_hash] = replace(self.rows[token_hash], revoked_at=now)


@dataclass
class StubQueries:
    """Запоминает вызовы и отдаёт то, что положил тест."""

    feed_result: list[FeedItem] = field(default_factory=list)
    published_result: EventDetails | None = None
    similar_result: list[FeedItem] = field(default_factory=list)
    authored_result: AuthoredEvent | None = None
    by_author_result: list[MyEventItem] = field(default_factory=list)
    queue_result: list[AuthoredEvent] = field(default_factory=list)
    calendar_result: list[CalendarDay] = field(default_factory=list)
    calls: list[tuple[str, tuple[Any, ...]]] = field(default_factory=list)

    async def feed(self, query: FeedQuery, viewer_id: UUID | None) -> list[FeedItem]:
        self.calls.append(("feed", (query, viewer_id)))
        return self.feed_result[: query.limit]

    async def published(self, event_id: UUID, viewer_id: UUID | None) -> EventDetails | None:
        self.calls.append(("published", (event_id, viewer_id)))
        return self.published_result

    async def similar(
        self, event_id: UUID, starts_from: datetime, viewer_id: UUID | None, limit: int
    ) -> list[FeedItem]:
        self.calls.append(("similar", (event_id, starts_from, viewer_id, limit)))
        return self.similar_result

    async def authored(self, event_id: UUID) -> AuthoredEvent | None:
        self.calls.append(("authored", (event_id,)))
        return self.authored_result

    async def by_author(self, author_id: UUID, status: EventStatus | None) -> list[MyEventItem]:
        self.calls.append(("by_author", (author_id, status)))
        return self.by_author_result

    async def moderation_queue(self, status: EventStatus) -> list[AuthoredEvent]:
        self.calls.append(("moderation_queue", (status,)))
        return self.queue_result

    async def calendar_month(self, year: int, month: int, tz: tzinfo) -> list[CalendarDay]:
        self.calls.append(("calendar_month", (year, month, tz)))
        return self.calendar_result


class FakeUnitOfWork:
    """Одна «база» на тест; ``commit`` запоминается, без него изменения откатываются."""

    def __init__(self) -> None:
        self.events = InMemoryEvents()
        self.users = InMemoryUsers()
        self.categories = InMemoryCategories()
        self.reactions = InMemoryReactions(self.events)
        self.moderation_log = InMemoryModerationLog()
        self.notifications = InMemoryNotifications()
        self.refresh_tokens = InMemoryRefreshTokens()
        self.email_verifications = InMemoryEmailVerifications()
        self.queries = StubQueries()
        self.commits = 0
        self._snapshot: dict[str, Any] = {}

    def _state(self) -> dict[str, Any]:
        return {
            "events": dict(self.events.rows),
            "users": dict(self.users.rows),
            "likes": set(self.reactions.likes),
            "favorites": set(self.reactions.favorites),
            "log": list(self.moderation_log.entries),
            "notifications": list(self.notifications.rows),
            "tokens": dict(self.refresh_tokens.rows),
            "verifications": dict(self.email_verifications.rows),
        }

    def _restore(self, s: dict[str, Any]) -> None:
        self.events.rows = s["events"]
        self.users.rows = s["users"]
        self.reactions.likes = s["likes"]
        self.reactions.favorites = s["favorites"]
        self.moderation_log.entries = s["log"]
        self.notifications.rows = s["notifications"]
        self.refresh_tokens.rows = s["tokens"]
        self.email_verifications.rows = s["verifications"]

    def __call__(self) -> Self:
        return self

    async def __aenter__(self) -> Self:
        self._snapshot = self._state()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._snapshot is not None:
            self._restore(self._snapshot)

    async def commit(self) -> None:
        self.commits += 1
        self._snapshot = self._state()


def category_ref(cid: int = 1) -> CategoryRef:
    return CategoryRef(cid, "concerts", "Концерты", "#7C3AED")
