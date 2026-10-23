"""Сценарий: открыть своё событие в форме редактирования (или модератору — целиком)."""

from uuid import UUID

from studlenta.application.dto import Actor, AuthoredEvent
from studlenta.application.ports import UnitOfWorkFactory
from studlenta.domain.errors import NotFoundError, PermissionDeniedError


class GetEventForEditing:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def __call__(self, actor: Actor, event_id: UUID) -> AuthoredEvent:
        async with self._uow() as uow:
            event = await uow.queries.authored(event_id)
        if event is None:
            raise NotFoundError("Событие")
        if event.author_id != actor.user_id and not actor.role.can_moderate:
            raise PermissionDeniedError("Это событие другого автора")
        return event
