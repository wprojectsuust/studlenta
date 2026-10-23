"""Общие проверки прав и загрузки, чтобы use case'ы оставались короткими."""

from uuid import UUID

from studlenta.application.dto import Actor
from studlenta.application.ports import UnitOfWork
from studlenta.domain.errors import NotFoundError, PermissionDeniedError
from studlenta.domain.events import Event


def require_moderator(actor: Actor) -> None:
    if not actor.role.can_moderate:
        raise PermissionDeniedError("Действие доступно только модераторам")


async def load_event(uow: UnitOfWork, event_id: UUID) -> Event:
    event = await uow.events.get(event_id)
    if event is None:
        raise NotFoundError("Событие")
    return event


async def load_own_event(uow: UnitOfWork, actor: Actor, event_id: UUID) -> Event:
    event = await load_event(uow, event_id)
    if event.author_id != actor.user_id:
        raise PermissionDeniedError("Это событие другого автора")
    return event
