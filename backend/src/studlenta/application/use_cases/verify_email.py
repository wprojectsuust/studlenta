"""Сценарий: переход по ссылке из письма — почта подтверждена."""

from studlenta.application.ports import Clock, TokenService, UnitOfWorkFactory
from studlenta.domain.errors import ValidationError

INVALID = "Ссылка не подошла — запросите новое письмо в профиле"
EXPIRED = "Ссылка устарела — запросите новое письмо в профиле"


class VerifyEmail:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock, tokens: TokenService) -> None:
        self._uow, self._clock, self._tokens = uow, clock, tokens

    async def __call__(self, token: str) -> None:
        now = self._clock.now()
        async with self._uow() as uow:
            record = await uow.email_verifications.get(self._tokens.hash_refresh_token(token))
            if not token or record is None:
                raise ValidationError({"token": INVALID})
            user = await uow.users.get(record.user_id)
            if user is None:
                raise ValidationError({"token": INVALID})
            if user.is_verified:
                return  # повторный переход по ссылке — не ошибка
            if record.expires_at <= now:
                raise ValidationError({"token": EXPIRED})
            await uow.users.mark_email_verified(user.id, now)
            await uow.commit()
