import pytest

from studlenta.application.use_cases.login_user import LoginUser
from studlenta.application.use_cases.refresh_session import RefreshSession
from studlenta.application.use_cases.register_user import RegisterUser
from studlenta.application.use_cases.request_password_reset import (
    RESET_TTL,
    RequestPasswordReset,
)
from studlenta.application.use_cases.reset_password import ResetPassword
from studlenta.domain.errors import AuthenticationError, ValidationError
from tests.fakes import FakeClock, FakeHasher, FakeMailer, FakeTokens, FakeUnitOfWork, SequentialIds

LINK = "https://karrad.tech/studlenta/reset-password"


@pytest.fixture
def mailer() -> FakeMailer:
    return FakeMailer()


@pytest.fixture
def tokens() -> FakeTokens:
    return FakeTokens()


@pytest.fixture
async def session(uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds, tokens: FakeTokens):  # type: ignore[no-untyped-def]
    return await RegisterUser(uow, clock, ids, FakeHasher(), tokens)(
        "anna@uust.ru", "password1", "Анна"
    )


def request(
    uow: FakeUnitOfWork, clock: FakeClock, tokens: FakeTokens, mailer: FakeMailer
) -> RequestPasswordReset:
    return RequestPasswordReset(uow, clock, tokens, mailer, LINK)


class TestRequest:
    async def test_sends_one_time_link(
        self, uow: FakeUnitOfWork, clock: FakeClock, tokens: FakeTokens, mailer: FakeMailer, session
    ) -> None:
        await request(uow, clock, tokens, mailer)(" ANNA@uust.ru ")
        [letter] = mailer.sent
        assert letter.to == "anna@uust.ru"
        assert "пароль" in letter.subject.lower()
        assert f"{LINK}?token=refresh-2" in letter.text
        [record] = uow.password_resets.rows.values()
        assert record.expires_at - record.created_at == RESET_TTL

    @pytest.mark.parametrize("email", ["nobody@uust.ru", "not-an-email"])
    async def test_unknown_email_is_silent(
        self,
        uow: FakeUnitOfWork,
        clock: FakeClock,
        tokens: FakeTokens,
        mailer: FakeMailer,
        email: str,
    ) -> None:
        await request(uow, clock, tokens, mailer)(
            email
        )  # без ошибки — нельзя узнать, есть ли аккаунт
        assert mailer.sent == []

    async def test_repeated_requests_are_throttled_silently(
        self, uow: FakeUnitOfWork, clock: FakeClock, tokens: FakeTokens, mailer: FakeMailer, session
    ) -> None:
        ask = request(uow, clock, tokens, mailer)
        await ask("anna@uust.ru")
        await ask("anna@uust.ru")
        assert len(mailer.sent) == 1
        clock.advance(minutes=2)
        await ask("anna@uust.ru")
        assert len(mailer.sent) == 2


class TestReset:
    async def test_new_password_works_old_sessions_die(
        self, uow: FakeUnitOfWork, clock: FakeClock, tokens: FakeTokens, mailer: FakeMailer, session
    ) -> None:
        await request(uow, clock, tokens, mailer)("anna@uust.ru")
        await ResetPassword(uow, clock, tokens, FakeHasher())("refresh-2", "new-password")

        with pytest.raises(AuthenticationError):
            await LoginUser(uow, clock, FakeHasher(), tokens)("anna@uust.ru", "password1")
        assert await LoginUser(uow, clock, FakeHasher(), tokens)("anna@uust.ru", "new-password")
        with pytest.raises(AuthenticationError):  # сессия, открытая до сброса, отозвана
            await RefreshSession(uow, clock, tokens)(session.refresh_token)
        [user] = uow.users.rows.values()
        assert user.is_verified  # доступ к ящику доказан

    async def test_link_is_one_time(
        self, uow: FakeUnitOfWork, clock: FakeClock, tokens: FakeTokens, mailer: FakeMailer, session
    ) -> None:
        await request(uow, clock, tokens, mailer)("anna@uust.ru")
        reset = ResetPassword(uow, clock, tokens, FakeHasher())
        await reset("refresh-2", "new-password")
        with pytest.raises(ValidationError) as exc:
            await reset("refresh-2", "other-password")
        assert "token" in exc.value.fields

    async def test_expired_link(
        self, uow: FakeUnitOfWork, clock: FakeClock, tokens: FakeTokens, mailer: FakeMailer, session
    ) -> None:
        await request(uow, clock, tokens, mailer)("anna@uust.ru")
        clock.advance(seconds=RESET_TTL.total_seconds() + 1)
        with pytest.raises(ValidationError, match="устарела"):
            await ResetPassword(uow, clock, tokens, FakeHasher())("refresh-2", "new-password")

    async def test_weak_password_keeps_link_usable(
        self, uow: FakeUnitOfWork, clock: FakeClock, tokens: FakeTokens, mailer: FakeMailer, session
    ) -> None:
        await request(uow, clock, tokens, mailer)("anna@uust.ru")
        reset = ResetPassword(uow, clock, tokens, FakeHasher())
        with pytest.raises(ValidationError) as exc:
            await reset("refresh-2", "short")
        assert "password" in exc.value.fields
        await reset("refresh-2", "long-enough")
