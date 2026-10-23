from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from studlenta.application.dto import Actor
from studlenta.domain.errors import AuthenticationError
from studlenta.presentation.api.container import Deps

_bearer = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


def optional_actor(c: Deps, credentials: Credentials) -> Actor | None:
    if credentials is None:
        return None
    return c.tokens.decode_access_token(credentials.credentials, now=c.clock.now())


def current_actor(actor: Annotated[Actor | None, Depends(optional_actor)]) -> Actor:
    if actor is None:
        raise AuthenticationError("Войдите, чтобы продолжить")
    return actor


CurrentActor = Annotated[Actor, Depends(current_actor)]
OptionalActor = Annotated[Actor | None, Depends(optional_actor)]
