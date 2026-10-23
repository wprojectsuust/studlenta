"""Сценарий: выход — refresh-токен больше не действует."""

from studlenta.application.ports import Clock, TokenService, UnitOfWorkFactory


class Logout:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock, tokens: TokenService) -> None:
        self._uow, self._clock, self._tokens = uow, clock, tokens

    async def __call__(self, refresh_token: str) -> None:
        async with self._uow() as uow:
            await uow.refresh_tokens.revoke(
                self._tokens.hash_refresh_token(refresh_token), self._clock.now()
            )
            await uow.commit()
