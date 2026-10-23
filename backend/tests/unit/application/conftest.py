from datetime import timedelta
from uuid import UUID

import pytest

from studlenta.application.dto import Actor, AuthoredEvent
from studlenta.domain.events import Event, EventContent, EventStatus
from studlenta.domain.users import Role, User
from tests.fakes import NOW, FakeClock, FakeUnitOfWork, SequentialIds, category_ref


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def ids() -> SequentialIds:
    return SequentialIds()


def content(**overrides: object) -> EventContent:
    data: dict[str, object] = {
        "title": "Вечер студенческой музыки",
        "summary": "Живой звук и любимые хиты. Вход свободный.",
        "body": "Группа «Путь» и приглашённые гости — большой концерт в актовом зале.",
        "category_id": 1,
        "place": "Актовый зал УУНиТ",
        "starts_at": NOW + timedelta(days=2),
        "ends_at": None,
    }
    data.update(overrides)
    return EventContent(**data)  # type: ignore[arg-type]


async def add_user(
    uow: FakeUnitOfWork, n: int, role: Role = Role.AUTHOR, *, verified: bool = True
) -> Actor:
    user_id = UUID(int=10_000 + n)
    await uow.users.add(
        User(
            user_id,
            f"user{n}@uust.ru",
            f"Пользователь {n}",
            role,
            "hashed:password1",
            NOW,
            email_verified_at=NOW if verified else None,
        )
    )
    return Actor(user_id, role)


async def add_event(
    uow: FakeUnitOfWork, author: Actor, *, n: int = 1, state: str = "draft"
) -> Event:
    event = Event.create_draft(
        event_id=UUID(int=20_000 + n), author_id=author.user_id, content=content(), now=NOW
    )
    if state != "draft":
        event.submit(now=NOW)
    if state == "published":
        event.approve(now=NOW)
    elif state == "changes_requested":
        event.request_changes(note="Поправьте место", now=NOW)
    elif state == "rejected":
        event.reject(note="Реклама", now=NOW)
    await uow.events.add(event)
    return event


def authored(**overrides: object) -> AuthoredEvent:
    data: dict[str, object] = {
        "id": UUID(int=20_001),
        "author_id": UUID(int=10_001),
        "author_name": "Пользователь 1",
        "status": EventStatus.PENDING,
        "title": "Вечер музыки",
        "summary": "Анонс",
        "body": "Описание",
        "category": category_ref(),
        "place": "Актовый зал",
        "starts_at": NOW + timedelta(days=2),
        "ends_at": None,
        "cover_url": None,
        "moderator_note": None,
        "submitted_at": NOW,
        "updated_at": NOW,
        "is_resubmission": False,
    }
    data.update(overrides)
    return AuthoredEvent(**data)  # type: ignore[arg-type]
