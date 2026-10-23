.PHONY: install lint format typecheck arch test test-unit test-integration test-e2e check db migrate run moderator reminders

install:          ## зависимости + git-хуки
	uv sync
	uv run pre-commit install --install-hooks -t pre-commit -t commit-msg

lint:             ## стиль и типичные ошибки
	uv run ruff check src tests
	uv run ruff format --check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

typecheck:
	uv run mypy

arch:             ## границы слоёв onion (import-linter)
	uv run lint-imports

test-unit:        ## домен и use cases на фейках, без Docker, < 1 c
	uv run pytest tests/unit -q

test-integration: ## SQL-репозитории на настоящем PostgreSQL (testcontainers)
	uv run pytest tests/integration -q

test-e2e:         ## сценарии через HTTP API
	uv run pytest tests/e2e -q

test:             ## всё + покрытие (порог 90%)
	uv run pytest --cov --cov-report=term-missing -q

check: lint typecheck arch test  ## то же, что CI

db:
	docker compose -f ../docker-compose.yml up -d db

migrate:
	uv run --env-file .env studlenta-migrate

run:
	uv run --env-file .env uvicorn studlenta.presentation.api.app:create_app --factory --reload

moderator:        ## make moderator EMAIL=... NAME="..."
	uv run --env-file .env studlenta-create-user --email "$(EMAIL)" --name "$(NAME)" --role moderator

reminders:        ## раз в час из cron/systemd timer
	uv run --env-file .env studlenta-send-reminders
