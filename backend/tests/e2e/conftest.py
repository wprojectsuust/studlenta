import json
import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import asyncpg
import httpx
import pytest
from fastapi import FastAPI

from studlenta.domain.users import Role
from studlenta.infrastructure.settings import Settings
from studlenta.presentation.api.app import create_app
from studlenta.presentation.cli import create_user_in_db
from tests.pg import clean_db, database_url, pool

__all__ = ["clean_db", "database_url", "pool"]
API = "/api/v1"


@pytest.fixture(autouse=True)
async def clean(clean_db: None) -> None:
    return clean_db


@pytest.fixture
def app(pool: asyncpg.Pool, database_url: str, tmp_path: Path) -> FastAPI:
    settings = Settings(
        database_url=database_url,
        jwt_secret="e2e-secret-" + "x" * 32,
        media_root=tmp_path / "media",
        secure_cookies=False,
        mail_outbox_dir=tmp_path / "mail",
        public_url="https://karrad.tech/studlenta",
    )
    return create_app(settings, pool=pool)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class Api:
    """Тонкая обёртка: клиент с токеном конкретного пользователя."""

    def __init__(self, client: httpx.AsyncClient, token: str | None = None) -> None:
        self.client, self.token = client, token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    async def get(self, path: str, **kw: Any) -> httpx.Response:
        return await self.client.get(API + path, headers=self._headers(), **kw)

    async def post(self, path: str, **kw: Any) -> httpx.Response:
        return await self.client.post(API + path, headers=self._headers(), **kw)

    async def put(self, path: str, **kw: Any) -> httpx.Response:
        return await self.client.put(API + path, headers=self._headers(), **kw)

    async def delete(self, path: str, **kw: Any) -> httpx.Response:
        return await self.client.delete(API + path, headers=self._headers(), **kw)


def outbox(app: FastAPI) -> Path:
    folder: Path = app.state.container.settings.mail_outbox_dir
    return folder


def last_link(app: FastAPI, email: str) -> str:
    letters = [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted(outbox(app).glob("*.json"))
    ]
    mine = [m for m in letters if m["to"] == email]
    assert mine, f"письмо для {email} не отправлено"
    match = re.search(r"token=([\w-]+)", mine[-1]["text"])
    assert match
    return match.group(1)


async def register(
    client: httpx.AsyncClient, email: str, name: str = "Анна", *, verify: bool = True
) -> Api:
    r = await client.post(
        f"{API}/auth/register", json={"email": email, "password": "password1", "full_name": name}
    )
    assert r.status_code == 201, r.text
    if verify:
        app: FastAPI = client._transport.app  # type: ignore[attr-defined]
        token = last_link(app, email)
        confirmed = await client.post(f"{API}/auth/verify-email", json={"token": token})
        assert confirmed.status_code == 204, confirmed.text
    return Api(client, r.json()["access_token"])


async def moderator(
    client: httpx.AsyncClient, pool: asyncpg.Pool, email: str = "mod@uust.ru"
) -> Api:
    await create_user_in_db(pool, email, "Елена Орлова", Role.MODERATOR, "password1")
    r = await client.post(f"{API}/auth/login", json={"email": email, "password": "password1"})
    assert r.status_code == 200, r.text
    return Api(client, r.json()["access_token"])
