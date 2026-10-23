"""Composition root: здесь (и только здесь) порты связываются с реализациями."""

from dataclasses import dataclass
from datetime import tzinfo
from typing import Annotated

import asyncpg
from fastapi import Depends, Request

from studlenta.infrastructure.db.uow import PostgresUnitOfWork
from studlenta.infrastructure.files import LocalFileStorage, PillowImageInspector
from studlenta.infrastructure.security import Argon2PasswordHasher, JwtTokenService
from studlenta.infrastructure.settings import Settings
from studlenta.infrastructure.system import SystemClock, UuidGenerator
from studlenta.presentation.api.rate_limit import FailureLimiter


@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings
    pool: asyncpg.Pool
    uow: PostgresUnitOfWork
    clock: SystemClock
    ids: UuidGenerator
    hasher: Argon2PasswordHasher
    tokens: JwtTokenService
    storage: LocalFileStorage
    images: PillowImageInspector
    login_limiter: FailureLimiter

    @property
    def tz(self) -> tzinfo:
        return self.settings.tz

    @classmethod
    def build(cls, settings: Settings, pool: asyncpg.Pool) -> "Container":
        return cls(
            settings=settings,
            pool=pool,
            uow=PostgresUnitOfWork(pool),
            clock=SystemClock(),
            ids=UuidGenerator(),
            hasher=Argon2PasswordHasher(),
            tokens=JwtTokenService(settings.jwt_secret.get_secret_value(), settings.access_ttl),
            storage=LocalFileStorage(settings.media_root, settings.public_media_url),
            images=PillowImageInspector(),
            login_limiter=FailureLimiter(max_failures=10, window_seconds=60),
        )


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


Deps = Annotated[Container, Depends(get_container)]
