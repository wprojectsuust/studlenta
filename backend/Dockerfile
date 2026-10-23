FROM python:3.13-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

RUN useradd --create-home app && mkdir -p /app/media && chown app /app/media
USER app
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)"
# Миграции идемпотентны и защищены advisory lock — безопасно запускать при каждом старте.
# STUDLENTA_ROOT_PATH (прод: /studlenta) уходит и в настройки приложения, и в ASGI root_path —
# по нему Swagger строит ссылки, когда nginx срезает префикс.
CMD ["sh", "-c", "uv run --no-sync studlenta-migrate && exec uv run --no-sync uvicorn studlenta.presentation.api.app:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*' --root-path \"${STUDLENTA_ROOT_PATH:-}\""]
