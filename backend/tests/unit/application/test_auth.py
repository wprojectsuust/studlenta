from uuid import UUID

import pytest

from studlenta.application.dto import Actor
from studlenta.application.use_cases.get_current_user import GetCurrentUser
from studlenta.application.use_cases.login_user import LoginUser
from studlenta.application.use_cases.logout import Logout
from studlenta.application.use_cases.refresh_session import REFRESH_TTL, RefreshSession
from studlenta.application.use_cases.register_user import RegisterUser
from studlenta.domain.errors import AuthenticationError, ValidationError
from studlenta.domain.users import Role
from tests.fakes import FakeClock, FakeHasher, FakeTokens, FakeUnitOfWork, SequentialIds


@pytest.fixture
def tokens() -> FakeTokens:
    return FakeTokens()


@pytest.fixture
def register(
    uow: FakeUnitOfWork, clock: FakeClock, ids: SequentialIds, tokens: FakeTokens
) -> RegisterUser:
    return RegisterUser(uow, clock, ids, FakeHasher(), tokens)


@pytest.fixture
def login(uow: FakeUnitOfWork, clock: FakeClock, tokens: FakeTokens) -> LoginUser:
    return LoginUser(uow, clock, FakeHasher(), tokens)


class TestRegister:
    async def test_creates_author_and_logs_in(
        self, uow: FakeUnitOfWork, register: RegisterUser, clock: FakeClock
    ) -> None:
        session = await register(" Anna@UUST.ru ", "password1", "Анна  Смирнова")
        [user] = uow.users.rows.values()
        assert user.email == "anna@uust.ru"
        assert user.full_name == "Анна Смирнова"
        assert user.role is Role.AUTHOR
        assert user.password_hash == "hashed:password1"
        assert not user.is_verified  # подтверждение — отдельным письмом
        assert session.access_token == f"access:{user.id}:author"
        assert session.refresh_expires_at == clock.now() + REFRESH_TTL
        assert "h(refresh-1)" in uow.refresh_tokens.rows

    async def test_email_taken(self, register: RegisterUser) -> None:
        await register("anna@uust.ru", "password1", "Анна")
        with pytest.raises(ValidationError) as exc:
            await register("ANNA@uust.ru", "password2", "Другая Анна")
        assert "email" in exc.value.fields

    async def test_all_field_errors_at_once(self, register: RegisterUser) -> None:
        with pytest.raises(ValidationError) as exc:
            await register("nope", "short", " ")
        assert set(exc.value.fields) == {"email", "password", "full_name"}


class TestLogin:
    async def test_success(self, register: RegisterUser, login: LoginUser) -> None:
        await register("anna@uust.ru", "password1", "Анна")
        session = await login("ANNA@uust.ru", "password1")
        assert session.access_token.startswith("access:")

    @pytest.mark.parametrize(
        ("email", "password"), [("anna@uust.ru", "wrong-pass"), ("nobody@uust.ru", "password1")]
    )
    async def test_same_error_for_wrong_pair(
        self, register: RegisterUser, login: LoginUser, email: str, password: str
    ) -> None:
        await register("anna@uust.ru", "password1", "Анна")
        with pytest.raises(AuthenticationError, match="Неверная почта или пароль"):
            await login(email, password)


class TestRefreshAndLogout:
    async def test_rotation_revokes_old_token(
        self, uow: FakeUnitOfWork, clock: FakeClock, tokens: FakeTokens, register: RegisterUser
    ) -> None:
        first = await register("anna@uust.ru", "password1", "Анна")
        refresh = RefreshSession(uow, clock, tokens)
        second = await refresh(first.refresh_token)
        assert second.refresh_token != first.refresh_token
        with pytest.raises(AuthenticationError):
            await refresh(first.refresh_token)

    async def test_expired(
        self, uow: FakeUnitOfWork, clock: FakeClock, tokens: FakeTokens, register: RegisterUser
    ) -> None:
        session = await register("anna@uust.ru", "password1", "Анна")
        clock.advance(seconds=REFRESH_TTL.total_seconds() + 1)
        with pytest.raises(AuthenticationError):
            await RefreshSession(uow, clock, tokens)(session.refresh_token)

    async def test_unknown_token(
        self, uow: FakeUnitOfWork, clock: FakeClock, tokens: FakeTokens
    ) -> None:
        with pytest.raises(AuthenticationError):
            await RefreshSession(uow, clock, tokens)("forged")

    async def test_logout(
        self, uow: FakeUnitOfWork, clock: FakeClock, tokens: FakeTokens, register: RegisterUser
    ) -> None:
        session = await register("anna@uust.ru", "password1", "Анна")
        await Logout(uow, clock, tokens)(session.refresh_token)
        await Logout(uow, clock, tokens)("unknown")  # не падает
        clock.advance(minutes=1)
        with pytest.raises(AuthenticationError):
            await RefreshSession(uow, clock, tokens)(session.refresh_token)


class TestCurrentUser:
    async def test_profile_with_unread(self, uow: FakeUnitOfWork, register: RegisterUser) -> None:
        await register("anna@uust.ru", "password1", "Анна")
        [user] = uow.users.rows.values()
        profile = await GetCurrentUser(uow)(Actor(user.id, user.role))
        assert (profile.email, profile.unread_notifications) == ("anna@uust.ru", 0)
        assert profile.email_verified is False

    async def test_deleted_user(self, uow: FakeUnitOfWork) -> None:
        with pytest.raises(AuthenticationError):
            await GetCurrentUser(uow)(Actor(UUID(int=1), Role.AUTHOR))
