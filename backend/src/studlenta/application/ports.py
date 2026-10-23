"""Порты: что application-слою нужно от внешнего мира.

Реализации живут в ``studlenta.infrastructure`` (PostgreSQL, argon2, JWT, диск),
а в юнит-тестах — в ``tests/fakes.py``.
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, tzinfo
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from studlenta.application.dto import (
    AuthoredEvent,
    CalendarDay,
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
from studlenta.domain.categories import Category
from studlenta.domain.events import Event, EventStatus
from studlenta.domain.users import User

# --- Окружение ---------------------------------------------------------------


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password_hash: str, password: str) -> bool: ...


class TokenService(Protocol):
    def issue_access_token(self, user: User, now: datetime) -> str: ...
    def new_refresh_token(self) -> str: ...
    def hash_refresh_token(self, token: str) -> str: ...


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None:
        """Отправляет письмо; при недоступности почты бросает исключение."""
        ...


class ReadCache(Protocol):
    """Кеш публичного чтения: значение по ключу на ``ttl`` секунд."""

    async def get_or_load[T](self, key: str, ttl: float, load: Callable[[], Awaitable[T]]) -> T: ...

    def invalidate(self, prefix: str = "") -> None:
        """Сбросить записи с префиксом (пустой — все)."""
        ...


class FileStorage(Protocol):
    async def save(self, name: str, data: bytes) -> str:
        """Сохраняет файл и возвращает публичный URL."""
        ...


class ImageInspector(Protocol):
    def inspect(self, data: bytes) -> ImageInfo | None:
        """Формат и размер картинки или ``None``, если это не картинка."""
        ...


# --- Запись (доменные сущности) ----------------------------------------------


class EventRepository(Protocol):
    async def get(self, event_id: UUID) -> Event | None: ...
    async def add(self, event: Event) -> None: ...

    async def update(self, event: Event) -> None:
        """Сохраняет с проверкой ``version``; при гонке — ``ConflictError``. Увеличивает version."""
        ...

    async def delete(self, event_id: UUID) -> None: ...


class UserRepository(Protocol):
    async def get(self, user_id: UUID) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...

    async def add(self, user: User) -> None:
        """При занятой почте — ``ConflictError``."""
        ...

    async def mark_email_verified(self, user_id: UUID, now: datetime) -> None: ...


class EmailVerificationRepository(Protocol):
    """Токены подтверждения почты; хранится только хеш токена."""

    async def add(self, record: EmailVerificationRecord) -> None: ...
    async def get(self, token_hash: str) -> EmailVerificationRecord | None: ...
    async def latest_created_at(self, user_id: UUID) -> datetime | None: ...


class CategoryRepository(Protocol):
    async def get(self, category_id: int) -> Category | None: ...
    async def list_with_counts(self, upcoming_from: datetime) -> list[CategoryWithCount]: ...


class ReactionRepository(Protocol):
    """Лайки и избранное. Все операции идемпотентны."""

    async def like(self, user_id: UUID, event_id: UUID, now: datetime) -> None: ...
    async def unlike(self, user_id: UUID, event_id: UUID) -> None: ...
    async def favorite(self, user_id: UUID, event_id: UUID, now: datetime) -> None: ...
    async def unfavorite(self, user_id: UUID, event_id: UUID) -> None: ...

    async def published_ids(self, event_ids: Sequence[UUID]) -> set[UUID]:
        """Какие из переданных событий сейчас опубликованы."""
        ...

    async def favorites_starting_between(
        self, start: datetime, end: datetime
    ) -> list[tuple[UUID, UUID, str]]:
        """(user_id, event_id, title) для избранных опубликованных событий в интервале."""
        ...


class ModerationLogRepository(Protocol):
    async def add(self, entry: ModerationLogEntry) -> None: ...
    async def list_for_event(self, event_id: UUID) -> list[ModerationLogEntry]: ...


class NotificationRepository(Protocol):
    async def add(self, notification: Notification) -> bool:
        """``False``, если такое уведомление (user, event, kind) уже было — для напоминаний."""
        ...

    async def list_for_user(
        self, user_id: UUID, limit: int, before: datetime | None
    ) -> list[Notification]: ...
    async def count_unread(self, user_id: UUID) -> int: ...
    async def mark_read(self, user_id: UUID, ids: Sequence[UUID] | None, now: datetime) -> None: ...


class RefreshTokenRepository(Protocol):
    async def add(self, record: RefreshTokenRecord) -> None: ...
    async def get(self, token_hash: str) -> RefreshTokenRecord | None: ...
    async def revoke(self, token_hash: str, now: datetime) -> None: ...


# --- Чтение (готовые DTO из SQL) ---------------------------------------------


@dataclass(frozen=True, slots=True)
class FeedQuery:
    starts_from: datetime
    starts_before: datetime | None
    category_slug: str | None = None
    search: str | None = None
    favorites_of: UUID | None = None
    after: tuple[datetime, UUID] | None = None  # keyset: (starts_at, id) последнего элемента
    limit: int = 20


class EventQueries(Protocol):
    async def feed(self, query: FeedQuery, viewer_id: UUID | None) -> list[FeedItem]: ...
    async def published(self, event_id: UUID, viewer_id: UUID | None) -> EventDetails | None: ...
    async def similar(
        self, event_id: UUID, starts_from: datetime, viewer_id: UUID | None, limit: int
    ) -> list[FeedItem]: ...
    async def authored(self, event_id: UUID) -> AuthoredEvent | None: ...
    async def by_author(self, author_id: UUID, status: EventStatus | None) -> list[MyEventItem]: ...
    async def moderation_queue(self, status: EventStatus) -> list[AuthoredEvent]: ...
    async def calendar_month(self, year: int, month: int, tz: tzinfo) -> list[CalendarDay]: ...


# --- Транзакция --------------------------------------------------------------


class UnitOfWork(Protocol):
    # Свойства только для чтения: так реализация может отдавать свои конкретные классы.
    @property
    def events(self) -> EventRepository: ...
    @property
    def users(self) -> UserRepository: ...
    @property
    def categories(self) -> CategoryRepository: ...
    @property
    def reactions(self) -> ReactionRepository: ...
    @property
    def moderation_log(self) -> ModerationLogRepository: ...
    @property
    def notifications(self) -> NotificationRepository: ...
    @property
    def refresh_tokens(self) -> RefreshTokenRepository: ...
    @property
    def email_verifications(self) -> EmailVerificationRepository: ...
    @property
    def queries(self) -> EventQueries: ...

    async def __aenter__(self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Без ``commit()`` изменения откатываются."""
        ...

    async def commit(self) -> None: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...
