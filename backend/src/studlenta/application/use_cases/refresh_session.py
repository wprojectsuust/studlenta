"""Сценарий: обновить access-токен по refresh-токену (с ротацией)."""

from studlenta.application.dto import Session
from studlenta.application.ports import Clock, TokenService, UnitOfWorkFactory
from studlenta.application.use_cases._sessions import REFRESH_TTL, open_session
from studlenta.domain.errors import AuthenticationError

__all__ = ["REFRESH_TTL", "RefreshSession"]


class RefreshSession:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock, tokens: TokenService) -> None:
        self._uow, self._clock, self._tokens = uow, clock, tokens

    async def __call__(self, refresh_token: str) -> Session:
        now = self._clock.now()
        token_hash = self._tokens.hash_refresh_token(refresh_token)
        async with self._uow() as uow:
            record = await uow.refresh_tokens.get(token_hash)
            if record is None or record.revoked_at is not None or record.expires_at <= now:
                raise AuthenticationError("Сессия истекла, войдите снова")
            user = await uow.users.get(record.user_id)
            if user is None:
                raise AuthenticationError("Сессия истекла, войдите снова")
            await uow.refresh_tokens.revoke(token_hash, now)
            session = await open_session(uow, self._tokens, user, now)
            await uow.commit()
        return session
