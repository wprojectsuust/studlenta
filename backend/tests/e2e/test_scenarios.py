"""Сквозные сценарии с холста дизайна — через HTTP, на настоящей базе."""

import io
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import asyncpg
import httpx
import pytest
from fastapi import FastAPI
from PIL import Image

from studlenta.infrastructure.settings import Settings
from studlenta.presentation.api.app import create_app
from tests.e2e.conftest import Api, last_link, moderator, outbox, register

pytestmark = pytest.mark.e2e
UFA = ZoneInfo("Asia/Yekaterinburg")


def future(days: int = 3, hour: int = 18) -> datetime:
    day = (datetime.now(UFA) + timedelta(days=days)).date()
    return datetime(day.year, day.month, day.day, hour, 0, tzinfo=UFA)


def event_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "title": "Вечер студенческой музыки",
        "summary": "Живой звук, любимые хиты и атмосфера студенческого концерта.",
        "body": "Группа «Путь» и приглашённые гости выступят в актовом зале. Вход свободный.",
        "category_id": 1,
        "place": "Актовый зал УУНиТ",
        "starts_at": future().isoformat(),
        "ends_at": None,
        "cover_url": None,
    }
    body.update(overrides)
    return body


def png(width: int = 1600, height: int = 900) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "#7C3AED").save(buf, "PNG")
    return buf.getvalue()


async def publish(author: Api, mod: Api, **overrides: object) -> str:
    event_id = (await author.post("/me/events", json=event_body(**overrides))).json()["id"]
    assert (await author.post(f"/me/events/{event_id}/submit")).status_code == 204
    assert (await mod.post(f"/moderation/events/{event_id}/approve")).status_code == 204
    return str(event_id)


class TestPremoderationJourney:
    """Автор → модератор → правки → публикация → лента, календарь, .ics."""

    async def test_full_cycle(self, client: httpx.AsyncClient, pool: asyncpg.Pool) -> None:
        author = await register(client, "ivan@uust.ru", "Иван Петров")
        mod = await moderator(client, pool)
        guest = Api(client)

        # Черновик с обложкой
        upload = await author.post("/uploads/cover", files={"file": ("c.png", png(), "image/png")})
        assert upload.status_code == 201, upload.text
        cover = upload.json()["url"]
        assert (await client.get(cover)).status_code == 200

        created = await author.post("/me/events", json=event_body(cover_url=cover))
        assert created.status_code == 201
        event_id = created.json()["id"]
        assert (await author.post(f"/me/events/{event_id}/submit")).status_code == 204

        # До одобрения событие не видно публично
        assert (await guest.get(f"/events/{event_id}")).status_code == 404
        assert (await guest.get("/events")).json()["items"] == []

        # Модератор возвращает на доработку
        queue = (await mod.get("/moderation/queue")).json()
        assert [e["id"] for e in queue] == [event_id]
        r = await mod.post(
            f"/moderation/events/{event_id}/request-changes",
            json={"note": "Укажите время окончания"},
        )
        assert r.status_code == 204

        mine = (await author.get("/me/events")).json()
        assert mine[0]["status"] == "changes_requested"
        assert mine[0]["moderator_note"] == "Укажите время окончания"
        inbox = (await author.get("/me/notifications")).json()
        assert inbox["unread"] == 1
        assert "Укажите время окончания" in inbox["items"][0]["text"]

        # Автор правит и отправляет снова — модератор видит пометку
        fixed = event_body(cover_url=cover, ends_at=future(hour=21).isoformat())
        assert (await author.put(f"/me/events/{event_id}", json=fixed)).status_code == 204
        assert (await author.post(f"/me/events/{event_id}/submit")).status_code == 204
        [item] = (await mod.get("/moderation/queue")).json()
        assert item["is_resubmission"] is True

        assert (await mod.post(f"/moderation/events/{event_id}/approve")).status_code == 204

        # Публично: лента, страница, календарь, категории, .ics
        feed = (await guest.get("/events")).json()
        assert [e["id"] for e in feed["items"]] == [event_id]
        today = (await guest.get("/events", params={"period": "today"})).json()
        assert today["items"] == []  # событие через три дня
        page = (await guest.get(f"/events/{event_id}")).json()
        assert page["organizer_name"] == "Иван Петров"
        assert page["category"]["color"] == "#7C3AED"
        assert page["cover_url"] == cover

        month = future().strftime("%Y-%m")
        days = (await guest.get("/calendar", params={"month": month})).json()
        assert {"date": future().date().isoformat(), "count": 1} in [
            {"date": d["date"], "count": d["count"]} for d in days
        ]
        day = await guest.get("/calendar/day", params={"date": future().date().isoformat()})
        assert [e["id"] for e in day.json()] == [event_id]

        cats = {c["slug"]: c["upcoming_count"] for c in (await guest.get("/categories")).json()}
        assert cats["concerts"] == 1

        ics = await guest.get(f"/events/{event_id}/ics")
        assert ics.headers["content-type"].startswith("text/calendar")
        assert "SUMMARY:Вечер студенческой музыки" in ics.text

        history = (await author.get(f"/events/{event_id}/history")).json()
        assert [h["action"] for h in history] == [
            "approved",
            "submitted",
            "changes_requested",
            "submitted",
        ]
        assert history[0]["actor_name"] == "Елена Орлова"

        # Автор снимает с публикации
        assert (await author.post(f"/events/{event_id}/archive")).status_code == 204
        assert (await guest.get(f"/events/{event_id}")).status_code == 404


class TestReactionsAndFeedFilters:
    async def test_likes_favorites_and_filters(
        self, client: httpx.AsyncClient, pool: asyncpg.Pool
    ) -> None:
        author = await register(client, "author@uust.ru")
        mod = await moderator(client, pool)
        concert = await publish(author, mod)
        football = await publish(
            author,
            mod,
            title="Турнир по мини-футболу",
            category_id=2,
            summary="Формат 5×5, приходите болеть",
            starts_at=future(days=4).isoformat(),
        )
        reader = await register(client, "reader@uust.ru")
        guest = Api(client)

        assert (await guest.put(f"/events/{concert}/like")).status_code == 401
        for _ in range(2):
            assert (await reader.put(f"/events/{concert}/like")).status_code == 204
        assert (await reader.put(f"/events/{football}/favorite")).status_code == 204

        feed = {e["id"]: e for e in (await reader.get("/events")).json()["items"]}
        assert (feed[concert]["likes_count"], feed[concert]["liked"]) == (1, True)
        assert feed[football]["favorited"] is True

        favs = (await reader.get("/events", params={"favorites": "true"})).json()["items"]
        assert [e["id"] for e in favs] == [football]
        assert (await guest.get("/events", params={"favorites": "true"})).status_code == 401

        sport = (await guest.get("/events", params={"category": "sport"})).json()["items"]
        assert [e["id"] for e in sport] == [football]
        found = (await guest.get("/events", params={"q": "футбол"})).json()["items"]
        assert [e["id"] for e in found] == [football]

        page1 = (await guest.get("/events", params={"limit": 1})).json()
        page2 = (
            await guest.get("/events", params={"limit": 1, "cursor": page1["next_cursor"]})
        ).json()
        assert [page1["items"][0]["id"], page2["items"][0]["id"]] == [concert, football]
        assert page2["next_cursor"] is None

        similar = (await guest.get(f"/events/{concert}/similar")).json()
        assert similar == []

        assert (await reader.delete(f"/events/{concert}/like")).status_code == 204
        guest_feed = (await guest.get("/events")).json()["items"]
        assert guest_feed[0]["likes_count"] == 0

        synced = await reader.post("/me/favorites/sync", json={"event_ids": [concert, football]})
        assert synced.json() == {"added": 2}


class TestAuthSessions:
    async def test_login_refresh_logout(self, client: httpx.AsyncClient) -> None:
        await register(client, "anna@uust.ru")
        bad = await client.post(
            "/api/v1/auth/login", json={"email": "anna@uust.ru", "password": "wrong-pass"}
        )
        assert bad.status_code == 401
        assert bad.json()["error"]["message"] == "Неверная почта или пароль"

        ok = await client.post(
            "/api/v1/auth/login", json={"email": "ANNA@uust.ru", "password": "password1"}
        )
        cookie = ok.cookies.get("refresh_token")
        assert cookie
        assert "httponly" in ok.headers["set-cookie"].lower()

        me = await Api(client, ok.json()["access_token"]).get("/me")
        assert me.json()["email"] == "anna@uust.ru"
        assert me.json()["role"] == "author"

        refreshed = await client.post("/api/v1/auth/refresh")
        assert refreshed.status_code == 200
        assert refreshed.cookies.get("refresh_token") != cookie

        client.cookies.set("refresh_token", cookie)  # старый токен после ротации не работает
        assert (await client.post("/api/v1/auth/refresh")).status_code == 401

        client.cookies.clear()
        assert (await client.post("/api/v1/auth/refresh")).status_code == 401
        assert (await client.post("/api/v1/auth/logout")).status_code == 204
        assert (await Api(client).get("/me")).status_code == 401
        assert (await Api(client, "garbage").get("/me")).status_code == 401

    async def test_validation_errors_are_per_field(self, client: httpx.AsyncClient) -> None:
        r = await client.post(
            "/api/v1/auth/register", json={"email": "nope", "password": "short", "full_name": ""}
        )
        assert r.status_code == 422
        assert set(r.json()["error"]["fields"]) == {"email", "password", "full_name"}

        author = await register(client, "anna@uust.ru")
        r = await author.post("/me/events", json=event_body(title=""))
        assert r.status_code == 422
        assert "title" in r.json()["error"]["fields"]

        r = await author.post("/me/events", json={"title": 5})
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "validation_error"

        draft = (await author.post("/me/events", json={"title": "Идея на потом"})).json()["id"]
        r = await author.post(f"/me/events/{draft}/submit")
        assert r.status_code == 422
        assert {"summary", "place", "starts_at"} <= set(r.json()["error"]["fields"])

        bad_cover = await author.post(
            "/uploads/cover", files={"file": ("x.png", png(800, 600), "image/png")}
        )
        assert bad_cover.status_code == 422
        assert "1200" in bad_cover.json()["error"]["fields"]["cover"]

    async def test_login_is_rate_limited(self, client: httpx.AsyncClient) -> None:
        codes = [
            (
                await client.post(
                    "/api/v1/auth/login", json={"email": "x@uust.ru", "password": "wrong-pass"}
                )
            ).status_code
            for _ in range(11)
        ]
        assert codes[:10] == [401] * 10
        assert codes[10] == 429


class TestPermissions:
    async def test_roles_and_conflicts(self, client: httpx.AsyncClient, pool: asyncpg.Pool) -> None:
        author = await register(client, "author@uust.ru")
        stranger = await register(client, "stranger@uust.ru")
        mod = await moderator(client, pool)
        other_mod = await moderator(client, pool, "mod2@uust.ru")

        event_id = (await author.post("/me/events", json=event_body())).json()["id"]
        assert (await stranger.put(f"/me/events/{event_id}", json=event_body())).status_code == 403
        assert (await stranger.get(f"/me/events/{event_id}")).status_code == 403
        assert (await author.get("/moderation/queue")).status_code == 403
        await author.post(f"/me/events/{event_id}/submit")

        r = await author.put(f"/me/events/{event_id}", json=event_body())
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "invalid_transition"

        own = (await mod.post("/me/events", json=event_body())).json()["id"]
        await mod.post(f"/me/events/{own}/submit")
        assert (await mod.post(f"/moderation/events/{own}/approve")).status_code == 403

        assert (await mod.post(f"/moderation/events/{event_id}/approve")).status_code == 204
        late = await other_mod.post(
            f"/moderation/events/{event_id}/reject", json={"note": "Поздно"}
        )
        assert late.status_code == 409

        assert (
            await mod.post("/moderation/events/00000000-0000-0000-0000-000000000000/approve")
        ).status_code == 404
        rejected = await other_mod.post(f"/moderation/events/{own}/reject", json={"note": " "})
        assert rejected.status_code == 422

        drafts = (await author.post("/me/events", json={"title": "Черновик"})).json()["id"]
        assert (await author.delete(f"/me/events/{drafts}")).status_code == 204
        assert (await author.delete(f"/me/events/{drafts}")).status_code == 404


class TestHealth:
    async def test_health_and_openapi(self, client: httpx.AsyncClient) -> None:
        assert (await client.get("/api/v1/health")).json() == {"status": "ok", "database": "ok"}
        spec = (await client.get("/api/v1/openapi.json")).json()
        assert spec["info"]["title"] == "Студлента УУНиТ API"


class TestAuthorCabinet:
    async def test_withdraw_cover_guard_and_inbox(
        self, client: httpx.AsyncClient, pool: asyncpg.Pool
    ) -> None:
        author = await register(client, "author@uust.ru")
        mod = await moderator(client, pool)

        for url in ("https://evil.example/x.png", "javascript:alert(1)", "/media/covers/../../x"):
            r = await author.post("/me/events", json=event_body(cover_url=url))
            assert r.status_code == 422, url
            assert "cover_url" in r.json()["error"]["fields"]

        event_id = (await author.post("/me/events", json=event_body())).json()["id"]
        await author.post(f"/me/events/{event_id}/submit")
        assert (await author.post(f"/me/events/{event_id}/withdraw")).status_code == 204
        [mine] = (await author.get("/me/events", params={"status": "draft"})).json()
        assert mine["id"] == event_id
        assert (await mod.get("/moderation/queue")).json() == []

        await author.post(f"/me/events/{event_id}/submit")
        await mod.post(f"/moderation/events/{event_id}/approve")
        assert (await author.get("/me")).json()["unread_notifications"] == 1
        assert (await author.post("/me/notifications/read", json={"ids": None})).status_code == 204
        assert (await author.get("/me/notifications")).json()["unread"] == 0


class TestBehindPathPrefix:
    """Прод живёт на karrad.tech/studlenta: nginx срезает префикс, приложение должно о нём знать."""

    async def test_cookie_path_media_url_and_docs_use_prefix(
        self, pool: asyncpg.Pool, database_url: str, tmp_path: Path
    ) -> None:
        settings = Settings(
            database_url=database_url, jwt_secret="p" * 40, media_root=tmp_path,
            secure_cookies=True, root_path="/studlenta",
        )  # fmt: skip
        app = create_app(settings, pool=pool)
        transport = httpx.ASGITransport(app=app, root_path="/studlenta")
        async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
            author = await register(client, "prefix@uust.ru", verify=False)
            set_cookie = (
                await client.post(
                    "/api/v1/auth/login", json={"email": "prefix@uust.ru", "password": "password1"}
                )
            ).headers["set-cookie"]
            assert "Path=/studlenta/api/v1/auth" in set_cookie
            assert "Secure" in set_cookie

            url = (
                await author.post("/uploads/cover", files={"file": ("c.png", png(), "image/png")})
            ).json()["url"]
            assert url.startswith("/studlenta/media/covers/")
            created = await author.post("/me/events", json=event_body(cover_url=url))
            assert created.status_code == 201

            feed = await client.get("/api/v1/events")
            assert feed.headers["cache-control"].startswith("public")

            docs = await client.get("/api/v1/docs")
            assert "/studlenta/api/v1/openapi.json" in docs.text


class TestEmailVerification:
    async def test_register_mail_link_and_resend(
        self, client: httpx.AsyncClient, app: FastAPI
    ) -> None:
        author = await register(client, "new@uust.ru", "Новый Автор", verify=False)
        me = (await author.get("/me")).json()
        assert me["email_verified"] is False

        event_id = (await author.post("/me/events", json=event_body())).json()["id"]
        blocked = await author.post(f"/me/events/{event_id}/submit")
        assert blocked.status_code == 403
        assert "Подтвердите почту" in blocked.json()["error"]["message"]

        too_soon = await author.post("/me/verify-email")
        assert too_soon.status_code == 409

        assert (
            await client.post("/api/v1/auth/verify-email", json={"token": "forged"})
        ).status_code == 422
        token = last_link(app, "new@uust.ru")
        assert (
            await client.post("/api/v1/auth/verify-email", json={"token": token})
        ).status_code == 204
        assert (await author.get("/me")).json()["email_verified"] is True
        assert (await author.post(f"/me/events/{event_id}/submit")).status_code == 204
        assert (await author.post("/me/verify-email")).json() == {"sent": False}

        letter = json.loads(sorted(outbox(app).glob("*.json"))[0].read_text(encoding="utf-8"))
        assert letter["subject"] == "Подтвердите почту — Студлента УУНиТ"
        assert "https://karrad.tech/studlenta/verify-email?token=" in letter["text"]


class TestCaching:
    async def test_cache_headers_and_instant_publication(
        self, client: httpx.AsyncClient, pool: asyncpg.Pool
    ) -> None:
        guest = Api(client)
        feed = await guest.get("/events")
        assert feed.headers["cache-control"] == "public, max-age=15, stale-while-revalidate=60"
        assert "authorization" in feed.headers["vary"].lower()
        assert (await guest.get("/categories")).headers["cache-control"].startswith("public")
        assert (await guest.get("/me")).headers["cache-control"] == "private, no-store"

        author = await register(client, "cache@uust.ru")
        assert (await author.get("/events")).headers["cache-control"] == "private, no-store"
        assert (await author.get("/me/events")).headers["cache-control"] == "private, no-store"

        mod = await moderator(client, pool)
        assert (await guest.get("/events")).json()["items"] == []  # пустая лента закешировалась
        event_id = await publish(author, mod)
        # Одобрение сбросило кеш — событие видно сразу, а не через 15 секунд
        assert [e["id"] for e in (await guest.get("/events")).json()["items"]] == [event_id]
        assert (await guest.get(f"/events/{event_id}")).status_code == 200
        assert (await author.post(f"/events/{event_id}/archive")).status_code == 204
        assert (await guest.get("/events")).json()["items"] == []
        assert (await guest.get(f"/events/{event_id}")).status_code == 404


class TestPasswordReset:
    async def test_forgot_password_flow(self, client: httpx.AsyncClient, app: FastAPI) -> None:
        await register(client, "forgot@uust.ru", verify=False)
        old_cookie = client.cookies.get("refresh_token")

        for email in ("forgot@uust.ru", "nobody@uust.ru"):  # ответ одинаковый — аккаунт не угадать
            r = await client.post("/api/v1/auth/password-reset", json={"email": email})
            assert (r.status_code, r.json()) == (202, {"sent": True})

        letters = [
            json.loads(p.read_text(encoding="utf-8")) for p in sorted(outbox(app).glob("*.json"))
        ]
        reset = [m for m in letters if m["subject"].startswith("Новый пароль")]
        assert [m["to"] for m in reset] == ["forgot@uust.ru"]
        token = reset[0]["text"].split("reset-password?token=")[1].split()[0]

        weak = await client.post(
            "/api/v1/auth/password-reset/confirm", json={"token": token, "password": "short"}
        )
        assert weak.status_code == 422
        done = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": token, "password": "brand-new-pass"},
        )
        assert done.status_code == 204
        again = await client.post(
            "/api/v1/auth/password-reset/confirm", json={"token": token, "password": "another-pass"}
        )
        assert again.status_code == 422

        old = await client.post(
            "/api/v1/auth/login", json={"email": "forgot@uust.ru", "password": "password1"}
        )
        assert old.status_code == 401
        new = await client.post(
            "/api/v1/auth/login", json={"email": "forgot@uust.ru", "password": "brand-new-pass"}
        )
        assert new.status_code == 200
        me = await Api(client, new.json()["access_token"]).get("/me")
        assert me.json()["email_verified"] is True

        client.cookies.set("refresh_token", old_cookie)
        assert (await client.post("/api/v1/auth/refresh")).status_code == 401


class TestInterests:
    """Просмотры → «Для вас» с объяснением → аналитика модератора и автора."""

    async def test_views_drive_recommendations_and_analytics(
        self, client: httpx.AsyncClient, pool: asyncpg.Pool
    ) -> None:
        author = await register(client, "org@uust.ru", "Оргкомитет")
        mod = await moderator(client, pool)
        jazz = await publish(author, mod, title="Джазовый вечер", starts_at=future(2).isoformat())
        choir = await publish(author, mod, title="Концерт хора", starts_at=future(4).isoformat())
        run = await publish(
            author, mod, title="Осенний забег", category_id=2, starts_at=future(1).isoformat()
        )
        guest = Api(client)
        me, other = "6f1c2a52-3c1d-4f0e-9a49-1b7f3c1f0a11", "0d9a8c51-6b55-4c0e-8f0e-7a1b2c3d4e5f"

        # Холодный старт: просмотров нет — ближайшие с пометкой «Скоро»
        cold = (await guest.get("/recommendations", params={"visitor": me})).json()
        assert [r["id"] for r in cold] == [run, jazz, choir]
        assert {(r["reason"], r["reason_kind"]) for r in cold} == {("Скоро", "soon")}

        for event_id, visitor in ((jazz, me), (jazz, other), (choir, other)):
            r = await guest.post(f"/events/{event_id}/view", json={"visitor_id": visitor})
            assert r.status_code == 204
        assert (await guest.post(f"/events/{jazz}/view", json={})).status_code == 422

        recs = await guest.get("/recommendations", params={"visitor": me})
        assert recs.headers["cache-control"] == "private, no-store"
        top = recs.json()[0]
        assert top["id"] == choir  # тот же жанр, и его смотрел другой зритель джаза
        assert top["reason"] == "Вы часто смотрите «Концерты»"
        assert jazz not in {r["id"] for r in recs.json()}  # уже видел

        report = (await mod.get("/analytics/interests", params={"days": 7})).json()
        assert report["scope"] == "all"
        assert report["totals"]["views"] == 3
        assert report["totals"]["viewers"] == 2
        assert report["top"][0]["title"] == "Джазовый вечер"
        assert report["categories"][0]["category"]["slug"] == "concerts"

        stranger = await register(client, "stranger@uust.ru", "Чужой автор")
        own = (await stranger.get("/analytics/interests")).json()
        assert own["scope"] == "mine"
        assert own["totals"]["views"] == 0
        assert (await guest.get("/analytics/interests")).status_code == 401
