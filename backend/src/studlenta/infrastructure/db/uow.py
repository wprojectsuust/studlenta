"""Unit of Work поверх транзакции asyncpg: одно соединение из пула на сценарий."""

from types import TracebackType
from typing import Self

import asyncpg
from asyncpg.pool import PoolConnectionProxy

from studlenta.infrastructure.db.queries import PgEventQueries
from studlenta.infrastructure.db.repositories import (
    PgCategoryRepository,
    PgEmailVerificationRepository,
    PgEventRepository,
    PgModerationLogRepository,
    PgNotificationRepository,
    PgReactionRepository,
    PgRefreshTokenRepository,
    PgUserRepository,
)


class PostgresTransaction:
    """Реализация порта ``UnitOfWork``. Без ``commit()`` всё откатывается."""

    events: PgEventRepository
    users: PgUserRepository
    categories: PgCategoryRepository
    reactions: PgReactionRepository
    moderation_log: PgModerationLogRepository
    notifications: PgNotificationRepository
    refresh_tokens: PgRefreshTokenRepository
    email_verifications: PgEmailVerificationRepository
    queries: PgEventQueries

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._conn: PoolConnectionProxy[asyncpg.Record] | None = None
        self._tx: asyncpg.transaction.Transaction | None = None
        self._committed = False

    async def __aenter__(self) -> Self:
        conn = await self._pool.acquire()
        self._conn = conn
        self._tx = conn.transaction()
        await self._tx.start()
        self.events = PgEventRepository(conn)
        self.users = PgUserRepository(conn)
        self.categories = PgCategoryRepository(conn)
        self.reactions = PgReactionRepository(conn)
        self.moderation_log = PgModerationLogRepository(conn)
        self.notifications = PgNotificationRepository(conn)
        self.refresh_tokens = PgRefreshTokenRepository(conn)
        self.email_verifications = PgEmailVerificationRepository(conn)
        self.queries = PgEventQueries(conn)
        return self

    async def commit(self) -> None:
        if self._tx is None:
            raise RuntimeError("commit() вызван вне async with")
        await self._tx.commit()
        self._committed = True

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if self._tx is not None and not self._committed:
                await self._tx.rollback()
        finally:
            if self._conn is not None:
                await self._pool.release(self._conn)


class PostgresUnitOfWork:
    """Фабрика UoW (порт ``UnitOfWorkFactory``): ``async with uow() as tx: ...``."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    def __call__(self) -> PostgresTransaction:
        return PostgresTransaction(self._pool)
