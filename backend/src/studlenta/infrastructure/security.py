"""Пароли (argon2id) и токены: короткий JWT для доступа и случайный refresh-токен.

Refresh-токен в базе хранится только как SHA-256: утечка таблицы не даёт войти.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from studlenta.application.dto import Actor
from studlenta.domain.errors import AuthenticationError
from studlenta.domain.users import Role, User

_ALGORITHM = "HS256"
MIN_SECRET = 32


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False


class JwtTokenService:
    def __init__(self, secret: str, access_ttl: timedelta) -> None:
        if len(secret) < MIN_SECRET:
            raise ValueError(f"JWT secret must be at least {MIN_SECRET} characters")
        self._secret, self._ttl = secret, access_ttl

    def issue_access_token(self, user: User, now: datetime) -> str:
        payload = {"sub": str(user.id), "role": user.role.value, "iat": now, "exp": now + self._ttl}
        return jwt.encode(payload, self._secret, algorithm=_ALGORITHM)

    def decode_access_token(self, token: str, now: datetime) -> Actor:
        try:
            payload = jwt.decode(
                token, self._secret, algorithms=[_ALGORITHM],
                options={"require": ["sub", "role", "exp"], "verify_exp": False},
            )  # fmt: skip
            if payload["exp"] <= now.timestamp():
                raise AuthenticationError("Токен истёк")
            return Actor(UUID(payload["sub"]), Role(payload["role"]))
        except (jwt.InvalidTokenError, ValueError, KeyError) as exc:
            raise AuthenticationError("Недействительный токен") from exc

    def new_refresh_token(self) -> str:
        return secrets.token_urlsafe(32)

    def hash_refresh_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
