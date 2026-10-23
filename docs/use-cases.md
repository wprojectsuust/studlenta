# Каталог сценариев (use cases)

Один сценарий — один класс в `backend/src/studlenta/application/use_cases/`.
Экраны — номера артбордов на [холсте](https://claude.ai/artifact/SMmtsEczRF13qMLb1YxwEw).
Все пути ниже — от `/api/v1`.

## Лента и событие (экраны 1, 2, 7)

| Use case | HTTP | Кто | Тесты |
|----------|------|-----|-------|
| `ListPublishedEvents` — период, категория, поиск, избранное, keyset-курсор | `GET /events` | все | unit `test_feed`, integration `TestFeed`, e2e |
| `GetPublishedEvent` | `GET /events/{id}` | все | unit, integration, e2e |
| `ListSimilarEvents` — та же категория, ближайшие | `GET /events/{id}/similar` | все | unit, integration, e2e |
| `GetEventIcs` — «Добавить в календарь» | `GET /events/{id}/ics` | все | unit, e2e |
| `ListCategories` — с числом предстоящих | `GET /categories` | все | unit, integration, e2e |
| `GetCalendarMonth` — сетка месяца по местному времени | `GET /calendar?month=2026-10` | все | unit, integration, e2e |
| `ListEventsByDay` | `GET /calendar/day?date=2026-10-29` | все | unit, e2e |

## Реакции

| Use case | HTTP | Кто |
|----------|------|-----|
| `LikeEvent` / `UnlikeEvent` | `PUT` / `DELETE /events/{id}/like` | вошедший |
| `AddToFavorites` / `RemoveFromFavorites` | `PUT` / `DELETE /events/{id}/favorite` | вошедший |
| `SyncGuestFavorites` — перенос избранного гостя из localStorage | `POST /me/favorites/sync` | вошедший |

## Автор (экраны 3, 5)

| Use case | HTTP | Переход |
|----------|------|---------|
| `CreateDraft` | `POST /me/events` | → `draft` |
| `GetEventForEditing` | `GET /me/events/{id}` | — (автор или модератор) |
| `UpdateDraft` | `PUT /me/events/{id}` | `draft`, `changes_requested` |
| `DeleteDraft` | `DELETE /me/events/{id}` | только `draft` |
| `SubmitForModeration` — только с подтверждённой почтой | `POST /me/events/{id}/submit` | `draft`/`changes_requested` → `pending` |
| `WithdrawSubmission` | `POST /me/events/{id}/withdraw` | `pending` → `draft` |
| `ArchiveEvent` | `POST /events/{id}/archive` | `published` → `archived` (автор или модератор) |
| `ListMyEvents` | `GET /me/events?status=` | — |
| `UploadCover` | `POST /uploads/cover` | — |

## Модерация (экран 4)

| Use case | HTTP | Переход | Побочные эффекты |
|----------|------|---------|------------------|
| `ListModerationQueue` | `GET /moderation/queue?status=` | — | старые сверху |
| `ApproveEvent` | `POST /moderation/events/{id}/approve` | `pending` → `published` | лог, уведомление автору |
| `RequestChanges` | `POST …/request-changes {note}` | `pending` → `changes_requested` | лог, уведомление с комментарием |
| `RejectEvent` | `POST …/reject {note}` | `pending` → `rejected` | лог, уведомление с причиной |
| `GetModerationHistory` | `GET /events/{id}/history` | — | автор и модераторы |

Общие правила модерации — в `use_cases/_moderation.py`: роль, запрет на своё событие,
одна транзакция «переход + журнал + уведомление».

## Вход и уведомления (экран 9, колокольчик)

| Use case | HTTP |
|----------|------|
| `RegisterUser` — роль `author`, сразу вход; письмо подтверждения уходит фоном | `POST /auth/register` |
| `RequestEmailVerification` — письмо со ссылкой, не чаще раза в минуту | `POST /me/verify-email` |
| `VerifyEmail` — переход по ссылке из письма | `POST /auth/verify-email` |
| `LoginUser` | `POST /auth/login` |
| `RefreshSession` — ротация refresh-токена | `POST /auth/refresh` (cookie) |
| `Logout` | `POST /auth/logout` |
| `GetCurrentUser` — имя, роль, непрочитанные | `GET /me` |
| `ListNotifications` | `GET /me/notifications` |
| `MarkNotificationsRead` | `POST /me/notifications/read` |
| `SendFavoriteReminders` — фоновый, раз в час | CLI `studlenta-send-reminders` |

## Вне скоупа MVP

- Комментарии к событиям — решено не делать (23.10.2026), реакции — лайк и избранное.
- Уведомления по e-mail или в Telegram — только in-app ([ADR-0008](adr/0008-in-app-notifications.md)).
