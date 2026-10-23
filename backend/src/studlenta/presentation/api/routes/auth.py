from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Request, Response, status

from studlenta.application.dto import Session
from studlenta.application.use_cases.get_current_user import GetCurrentUser
from studlenta.application.use_cases.login_user import WRONG_PAIR, LoginUser
from studlenta.application.use_cases.logout import Logout
from studlenta.application.use_cases.refresh_session import RefreshSession
from studlenta.application.use_cases.register_user import RegisterUser
from studlenta.application.use_cases.request_email_verification import RequestEmailVerification
from studlenta.application.use_cases.verify_email import VerifyEmail
from studlenta.domain.errors import AuthenticationError
from studlenta.presentation.api.container import Container, Deps
from studlenta.presentation.api.deps import CurrentActor
from studlenta.presentation.api.rate_limit import TooManyAttemptsError
from studlenta.presentation.api.schemas import (
    LoginIn,
    ProfileOut,
    RegisterIn,
    SentOut,
    TokenIn,
    TokenOut,
)

router = APIRouter(tags=["Вход"])
COOKIE = "refresh_token"
RefreshCookie = Annotated[str | None, Cookie(alias=COOKIE)]


def _cookie_path(c: Container) -> str:
    return f"{c.settings.root_path}/api/v1/auth"


def _respond(c: Container, session: Session, response: Response) -> TokenOut:
    response.set_cookie(
        COOKIE, session.refresh_token, httponly=True, secure=c.settings.secure_cookies,
        samesite="strict", path=_cookie_path(c),
        max_age=int((session.refresh_expires_at - c.clock.now()).total_seconds()),
    )  # fmt: skip
    return TokenOut(
        access_token=session.access_token, expires_in=int(c.settings.access_ttl.total_seconds())
    )


def _verification(c: Container) -> RequestEmailVerification:
    return RequestEmailVerification(c.uow, c.clock, c.tokens, c.mailer, c.verify_link)


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterIn, c: Deps, response: Response, background: BackgroundTasks
) -> TokenOut:
    session = await RegisterUser(c.uow, c.clock, c.ids, c.hasher, c.tokens)(
        body.email, body.password, body.full_name
    )
    # Письмо уходит после ответа: медленный SMTP не задерживает регистрацию.
    background.add_task(_verification(c), session.actor)
    return _respond(c, session, response)


@router.post("/auth/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def verify_email(body: TokenIn, c: Deps) -> None:
    await VerifyEmail(c.uow, c.clock, c.tokens)(body.token)


@router.post("/me/verify-email", responses={409: {"description": "Письмо уже отправлено"}})
async def resend_verification(c: Deps, actor: CurrentActor) -> SentOut:
    return SentOut(sent=await _verification(c)(actor))


@router.post("/auth/login", responses={429: {"description": "Слишком много попыток"}})
async def login(body: LoginIn, c: Deps, request: Request, response: Response) -> TokenOut:
    key = f"{request.client.host if request.client else '?'}:{body.email.strip().lower()}"
    if c.login_limiter.is_blocked(key):
        raise TooManyAttemptsError
    try:
        session = await LoginUser(c.uow, c.clock, c.hasher, c.tokens)(body.email, body.password)
    except AuthenticationError:
        c.login_limiter.register_failure(key)
        raise AuthenticationError(WRONG_PAIR) from None
    c.login_limiter.reset(key)
    return _respond(c, session, response)


@router.post("/auth/refresh")
async def refresh(c: Deps, response: Response, token: RefreshCookie = None) -> TokenOut:
    if not token:
        raise AuthenticationError("Сессия истекла, войдите снова")
    session = await RefreshSession(c.uow, c.clock, c.tokens)(token)
    return _respond(c, session, response)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(c: Deps, response: Response, token: RefreshCookie = None) -> None:
    if token:
        await Logout(c.uow, c.clock, c.tokens)(token)
    response.delete_cookie(COOKIE, path=_cookie_path(c))


@router.get("/me")
async def me(c: Deps, actor: CurrentActor) -> ProfileOut:
    p = await GetCurrentUser(c.uow)(actor)
    return ProfileOut(
        id=p.id,
        email=p.email,
        full_name=p.full_name,
        role=p.role,
        unread_notifications=p.unread_notifications,
        email_verified=p.email_verified,
    )
