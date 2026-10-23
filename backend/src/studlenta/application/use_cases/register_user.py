"""Сценарий: регистрация студента (роль author) с мгновенным входом."""

from studlenta.application.dto import Session
from studlenta.application.ports import (
    Clock,
    IdGenerator,
    PasswordHasher,
    TokenService,
    UnitOfWorkFactory,
)
from studlenta.application.use_cases._sessions import open_session
from studlenta.domain.errors import ConflictError, ValidationError
from studlenta.domain.users import Role, User, normalize_email, normalize_name, validate_password

EMAIL_TAKEN = {"email": "Эта почта уже зарегистрирована"}


def _collect(*checks: object) -> None:
    errors: dict[str, str] = {}
    for check in checks:
        try:
            check()  # type: ignore[operator]
        except ValidationError as exc:
            errors.update(exc.fields)
    if errors:
        raise ValidationError(errors)


class RegisterUser:
    def __init__(
        self,
        uow: UnitOfWorkFactory,
        clock: Clock,
        ids: IdGenerator,
        hasher: PasswordHasher,
        tokens: TokenService,
    ) -> None:
        self._uow, self._clock, self._ids = uow, clock, ids
        self._hasher, self._tokens = hasher, tokens

    async def __call__(self, email: str, password: str, full_name: str) -> Session:
        _collect(
            lambda: normalize_email(email),
            lambda: validate_password(password),
            lambda: normalize_name(full_name),
        )
        now = self._clock.now()
        user = User(
            self._ids.new_id(),
            normalize_email(email),
            normalize_name(full_name),
            Role.AUTHOR,
            self._hasher.hash(password),
            now,
        )
        async with self._uow() as uow:
            if await uow.users.get_by_email(user.email):
                raise ValidationError(EMAIL_TAKEN)
            try:
                await uow.users.add(user)
            except ConflictError as exc:
                raise ValidationError(EMAIL_TAKEN) from exc
            session = await open_session(uow, self._tokens, user, now)
            await uow.commit()
        return session
