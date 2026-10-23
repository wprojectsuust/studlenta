from datetime import timedelta

import pytest

from studlenta.application.use_cases.request_email_verification import (
    RESEND_COOLDOWN,
    TOKEN_TTL,
    RequestEmailVerification,
)
from studlenta.application.use_cases.submit_for_moderation import SubmitForModeration
from studlenta.application.use_cases.verify_email import VerifyEmail
from studlenta.domain.errors import ConflictError, PermissionDeniedError, ValidationError
from studlenta.domain.events import EventStatus
from tests.fakes import FakeClock, FakeMailer, FakeTokens, FakeUnitOfWork
from tests.unit.application.conftest import add_event, add_user

LINK = "https://karrad.tech/studlenta/verify-email"


@pytest.fixture
def mailer() -> FakeMailer:
    return FakeMailer()


@pytest.fixture
def request_link(
    uow: FakeUnitOfWork, clock: FakeClock, mailer: FakeMailer
) -> RequestEmailVerification:
    return RequestEmailVerification(uow, clock, FakeTokens(), mailer, LINK)


class TestRequest:
    async def test_sends_a_link_with_a_one_time_token(
        self, uow: FakeUnitOfWork, request_link: RequestEmailVerification, mailer: FakeMailer
    ) -> None:
        user = await add_user(uow, 1, verified=False)
        assert await request_link(user) is True

        [message] = mailer.sent
        assert message.to == "user1@uust.ru"
        assert "Подтвердите почту" in message.subject
        assert f"{LINK}?token=refresh-1" in message.text
        assert f"{LINK}?token=refresh-1" in message.html
        [record] = uow.email_verifications.rows.values()
        assert record.token_hash == "h(refresh-1)"
        assert record.expires_at - record.created_at == TOKEN_TTL

    async def test_resend_only_after_cooldown(
        self,
        uow: FakeUnitOfWork,
        clock: FakeClock,
        request_link: RequestEmailVerification,
        mailer: FakeMailer,
    ) -> None:
        user = await add_user(uow, 1, verified=False)
        await request_link(user)
        clock.advance(seconds=10)
        with pytest.raises(ConflictError, match="минут"):
            await request_link(user)
        clock.advance(seconds=RESEND_COOLDOWN.total_seconds())
        await request_link(user)
        assert len(mailer.sent) == 2

    async def test_verified_user_gets_nothing(
        self, uow: FakeUnitOfWork, request_link: RequestEmailVerification, mailer: FakeMailer
    ) -> None:
        user = await add_user(uow, 1)
        assert await request_link(user) is False
        assert mailer.sent == []

    async def test_mail_failure_does_not_break_the_flow(
        self, uow: FakeUnitOfWork, request_link: RequestEmailVerification, mailer: FakeMailer
    ) -> None:
        mailer.fail = True
        user = await add_user(uow, 1, verified=False)
        assert await request_link(user) is False
        assert len(uow.email_verifications.rows) == 1  # токен сохранён — можно запросить ещё раз


class TestVerify:
    async def test_link_verifies_once(
        self, uow: FakeUnitOfWork, clock: FakeClock, request_link: RequestEmailVerification
    ) -> None:
        user = await add_user(uow, 1, verified=False)
        await request_link(user)
        verify = VerifyEmail(uow, clock, FakeTokens())
        await verify("refresh-1")
        stored = uow.users.rows[user.user_id]
        assert stored.email_verified_at == clock.now()
        assert stored.is_verified
        await verify("refresh-1")  # повторный переход по ссылке — не ошибка

    @pytest.mark.parametrize("token", ["forged", ""])
    async def test_unknown_link(self, uow: FakeUnitOfWork, clock: FakeClock, token: str) -> None:
        with pytest.raises(ValidationError) as exc:
            await VerifyEmail(uow, clock, FakeTokens())(token)
        assert "token" in exc.value.fields

    async def test_expired_link(
        self, uow: FakeUnitOfWork, clock: FakeClock, request_link: RequestEmailVerification
    ) -> None:
        user = await add_user(uow, 1, verified=False)
        await request_link(user)
        clock.advance(seconds=TOKEN_TTL.total_seconds() + 1)
        with pytest.raises(ValidationError, match="устарела"):
            await VerifyEmail(uow, clock, FakeTokens())("refresh-1")
        assert not uow.users.rows[user.user_id].is_verified


class TestSubmitNeedsVerifiedEmail:
    async def test_unverified_author_cannot_submit(
        self, uow: FakeUnitOfWork, clock: FakeClock
    ) -> None:
        author = await add_user(uow, 1, verified=False)
        event = await add_event(uow, author)
        with pytest.raises(PermissionDeniedError, match="Подтвердите почту"):
            await SubmitForModeration(uow, clock)(author, event.id)
        assert uow.events.rows[event.id].status is EventStatus.DRAFT

    async def test_after_verification_submit_works(
        self, uow: FakeUnitOfWork, clock: FakeClock, request_link: RequestEmailVerification
    ) -> None:
        author = await add_user(uow, 1, verified=False)
        event = await add_event(uow, author)
        await request_link(author)
        await VerifyEmail(uow, clock, FakeTokens())("refresh-1")
        clock.advance(minutes=1)
        await SubmitForModeration(uow, clock)(author, event.id)
        assert uow.events.rows[event.id].status is EventStatus.PENDING
        assert timedelta(0) < RESEND_COOLDOWN
