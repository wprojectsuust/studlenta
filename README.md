# Студлента УУНиТ

Лента студенческих мероприятий с **обязательной предмодерацией**: студент предлагает событие,
модератор одобряет, возвращает на доработку или отклоняет — и только после этого событие
появляется в ленте. Прототип для хакатона УУНиТ.

- **Прод:** https://karrad.tech/studlenta (API: `/studlenta/api/v1/docs`)
- **Деплой и CI/CD:** [docs/deploy.md](docs/deploy.md)
- **Дизайн (холст):** https://claude.ai/artifact/SMmtsEczRF13qMLb1YxwEw — 9 экранов, 4 скина, WCAG 2.1 AA
- **Спецификация для фронтенда:** [docs/design/handoff.md](docs/design/handoff.md)

## Что умеет

| Роль | Возможности |
|------|-------------|
| Гость | лента с фильтрами «Сегодня / На неделе / В месяце», категории, поиск по-русски (с морфологией), календарь, страница события, `.ics` |
| Студент (author) | всё выше + лайки, избранное, черновики, обложки, отправка на модерацию, статусы «Мои публикации», уведомления |
| Модератор | очередь (старые сверху), одобрить / вернуть с комментарием / отклонить с причиной, история решений |

Полный каталог сценариев — [docs/use-cases.md](docs/use-cases.md).

## Стек

**Бэкенд:** FastAPI (async) · asyncpg с **нативным SQL** (без ORM) · PostgreSQL 16 ·
onion-архитектура, **отдельный use case на каждый сценарий** · pytest: unit / integration
(testcontainers) / e2e · ruff, mypy `--strict`, import-linter.

**Фронтенд:** Next.js 16 (App Router, SSR страницы события для превью в соцсетях) · TanStack Query ·
CSS-переменные и 4 скина · Vitest + Testing Library · Playwright + axe (WCAG 2.1 AA) на полном стеке.

**Поставка:** Docker · GitHub Actions → GHCR → VPS с автооткатом.

Почему так — в [ADR](docs/adr/). Как устроено — [docs/architecture.md](docs/architecture.md).

## Быстрый старт

Нужны Docker и [uv](https://docs.astral.sh/uv/).

```bash
docker compose up -d db                     # PostgreSQL на localhost:5432
cd backend
make install                                # зависимости + git-хуки
cp .env.example .env                        # и впишите STUDLENTA_JWT_SECRET (≥ 32 символа)
make migrate                                # схема и категории
make moderator EMAIL=mod@uust.ru NAME="Модератор"
STUDLENTA_ROOT_PATH=/studlenta make run      # API на :8000

cd ../frontend
npm ci
npm run dev                                 # http://localhost:3000/studlenta (проксирует /api в :8000)
```

Всё в контейнерах: `docker compose up --build` из корня → http://localhost:3000/studlenta.

## Проверки

```bash
cd backend && make check     # ruff + mypy --strict + границы слоёв + тесты, покрытие ≥ 90 %
cd frontend && npm run check # eslint + tsc + vitest (включая контраст токенов всех скинов)
cd frontend && npm run e2e   # Playwright + axe; нужен поднятый стек (см. CONTRIBUTING)
```

## Структура

```
backend/
  src/studlenta/
    domain/          сущности и правила: Event (машина статусов), User, Category, периоды
    application/     use_cases/ (по файлу на сценарий), ports.py (интерфейсы), dto.py
    infrastructure/  db/ (SQL, миграции, UoW), security (argon2, JWT), files, settings
    presentation/    api/ (FastAPI-роутеры, схемы, ошибки), cli.py
  tests/
    unit/            домен и use cases на in-memory фейках
    integration/     SQL-репозитории на настоящем PostgreSQL
    e2e/             сценарии через HTTP
frontend/
  src/app/           страницы (App Router): лента, событие, календарь, кабинет, модерация, вход
  src/components/    UI: карточка, форма, панель модерации, каркас с сайдбаром и таб-баром
  src/lib/           API-клиент, авторизация, запросы, форматирование дат, скины
  e2e/               сценарии Playwright + axe
deploy/              прод: compose, скрипт деплоя, nginx
docs/                архитектура, ADR, сценарии, дизайн, деплой
```

## Как участвовать

Перед первым PR прочитайте [CONTRIBUTING.md](CONTRIBUTING.md): там TDD-цикл, правила слоёв,
формат коммитов и чек-лист «готово». Большую часть правил проверяют хуки и CI автоматически.

## Лицензия

[MIT](LICENSE)
