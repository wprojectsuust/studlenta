"""Сценарий: вход по почте и паролю."""

from studlenta.application.dto import Session
from studlenta.application.ports import Clock, PasswordHasher, TokenService, UnitOfWorkFactory
from studlenta.application.use_cases._sessions import open_session
from studlenta.domain.errors import AuthenticationError, ValidationError
from studlenta.domain.users import normalize_email

WRONG_PAIR = "Неверная почта или пароль"
# Проверяем пароль и для несуществующей почты, чтобы по времени ответа нельзя было
# узнать, зарегистрирован ли адрес.
_DUMMY_HASH = "dummy"


class LoginUser:
    def __init__(
        self, uow: UnitOfWorkFactory, clock: Clock, hasher: PasswordHasher, tokens: TokenService
    ) -> None:
        self._uow, self._clock, self._hasher, self._tokens = uow, clock, hasher, tokens

    async def __call__(self, email: str, password: str) -> Session:
        try:
            normalized = normalize_email(email)
        except ValidationError as exc:
            raise AuthenticationError(WRONG_PAIR) from exc
        async with self._uow() as uow:
            user = await uow.users.get_by_email(normalized)
            valid = self._hasher.verify(user.password_hash if user else _DUMMY_HASH, password)
            if user is None or not valid:
                raise AuthenticationError(WRONG_PAIR)
            session = await open_session(uow, self._tokens, user, self._clock.now())
            await uow.commit()
        return session
