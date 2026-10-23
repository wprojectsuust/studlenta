import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import asyncpg
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from studlenta.infrastructure.settings import Settings
from studlenta.presentation.api.container import Container, Deps
from studlenta.presentation.api.errors import install_error_handlers
from studlenta.presentation.api.routes import auth, author, interests, moderation, public

PREFIX = "/api/v1"
# Публичное чтение, одинаковое для всех гостей (ленты, событие, календарь, категории).
_PUBLIC_GET = re.compile(
    r"^/api/v1/(events(/[0-9a-f-]{36}(/similar|/ics)?)?|categories|calendar(/day)?)$"
)
GUEST_CACHE = "public, max-age=15, stale-while-revalidate=60"
NO_STORE = "private, no-store"


def create_app(settings: Settings | None = None, pool: asyncpg.Pool | None = None) -> FastAPI:
    """Собирает приложение. ``pool`` передают тесты; иначе он создаётся при старте."""
    settings = settings or Settings()  # type: ignore[call-arg]  # значения берутся из окружения

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        own_pool = pool is None
        db = pool or await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
        app.state.container = Container.build(settings, db)
        try:
            yield
        finally:
            if own_pool:
                await db.close()

    app = FastAPI(
        title="Студлента УУНиТ API",
        version="0.1.0",
        lifespan=lifespan,
        openapi_url=f"{PREFIX}/openapi.json",
        docs_url=f"{PREFIX}/docs",
        redoc_url=None,
    )
    if pool is not None:  # ASGI-клиент в тестах не вызывает lifespan
        app.state.container = Container.build(settings, pool)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )
    install_error_handlers(app)

    @app.middleware("http")
    async def cache_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        # За nginx путь может прийти с префиксом /studlenta (ASGI root_path) — срезаем его.
        root = request.scope.get("root_path", "")
        path = request.url.path
        if root and path.startswith(root):
            path = path[len(root) :]
        if not path.startswith(PREFIX) or "cache-control" in response.headers:
            return response
        guest = "authorization" not in request.headers
        public = request.method == "GET" and response.status_code == 200 and guest
        if public and _PUBLIC_GET.match(path):
            response.headers["Cache-Control"] = GUEST_CACHE
            # Без токена и с токеном ответы разные (флаги «лайкнул») — кеш браузера их различает.
            response.headers["Vary"] = "Authorization"
        else:
            response.headers["Cache-Control"] = NO_STORE
        return response

    system = APIRouter(tags=["Служебное"])

    @system.get("/health")
    async def health(c: Deps) -> dict[str, str]:
        await c.pool.fetchval("SELECT 1")
        return {"status": "ok", "database": "ok"}

    routers = (system, auth.router, public.router, interests.router, author.router)
    for router in (*routers, moderation.router):
        app.include_router(router, prefix=PREFIX)

    settings.media_root.mkdir(parents=True, exist_ok=True)
    app.mount(settings.media_url, StaticFiles(directory=settings.media_root), name="media")
    return app
