"""Сценарий: переход по ссылке из письма и новый пароль. Все прежние сессии отзываются."""

from studlenta.application.ports import Clock, PasswordHasher, TokenService, UnitOfWorkFactory
from studlenta.domain.errors import ValidationError
from studlenta.domain.users import validate_password

INVALID = "Ссылка не подошла — запросите новое письмо"
EXPIRED = "Ссылка устарела — запросите новое письмо"


class ResetPassword:
    def __init__(
        self, uow: UnitOfWorkFactory, clock: Clock, tokens: TokenService, hasher: PasswordHasher
    ) -> None:
        self._uow, self._clock, self._tokens, self._hasher = uow, clock, tokens, hasher

    async def __call__(self, token: str, new_password: str) -> None:
        validate_password(new_password)
        now = self._clock.now()
        token_hash = self._tokens.hash_refresh_token(token)
        async with self._uow() as uow:
            record = await uow.password_resets.get(token_hash)
            if not token or record is None or record.used_at is not None:
                raise ValidationError({"token": INVALID})
            if record.expires_at <= now:
                raise ValidationError({"token": EXPIRED})
            await uow.users.update_password(record.user_id, self._hasher.hash(new_password))
            await uow.users.mark_email_verified(record.user_id, now)  # доступ к ящику доказан
            await uow.refresh_tokens.revoke_all(record.user_id, now)  # чужие сессии — долой
            await uow.password_resets.mark_used(token_hash, now)
            await uow.commit()
