from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from studlenta.infrastructure.settings import Settings
from studlenta.presentation.api.container import Container, Deps
from studlenta.presentation.api.errors import install_error_handlers
from studlenta.presentation.api.routes import auth, author, moderation, public

PREFIX = "/api/v1"


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

    system = APIRouter(tags=["Служебное"])

    @system.get("/health")
    async def health(c: Deps) -> dict[str, str]:
        await c.pool.fetchval("SELECT 1")
        return {"status": "ok", "database": "ok"}

    for router in (system, auth.router, public.router, author.router, moderation.router):
        app.include_router(router, prefix=PREFIX)

    settings.media_root.mkdir(parents=True, exist_ok=True)
    app.mount(settings.media_url, StaticFiles(directory=settings.media_root), name="media")
    return app
