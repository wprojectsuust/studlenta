from datetime import datetime, timedelta

from studlenta.application.dto import Actor, RefreshTokenRecord, Session
from studlenta.application.ports import TokenService, UnitOfWork
from studlenta.domain.users import User

REFRESH_TTL = timedelta(days=30)


async def open_session(uow: UnitOfWork, tokens: TokenService, user: User, now: datetime) -> Session:
    refresh = tokens.new_refresh_token()
    expires = now + REFRESH_TTL
    await uow.refresh_tokens.add(
        RefreshTokenRecord(tokens.hash_refresh_token(refresh), user.id, expires, None)
    )
    return Session(
        tokens.issue_access_token(user, now), refresh, expires, Actor(user.id, user.role)
    )
