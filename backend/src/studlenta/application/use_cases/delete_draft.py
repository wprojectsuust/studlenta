"""Сценарий: автор удаляет черновик. Отправленные события не удаляются — только архив."""

from uuid import UUID

from studlenta.application.dto import Actor
from studlenta.application.guards import load_own_event
from studlenta.application.ports import UnitOfWorkFactory
from studlenta.domain.errors import InvalidTransitionError


class DeleteDraft:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def __call__(self, actor: Actor, event_id: UUID) -> None:
        async with self._uow() as uow:
            event = await load_own_event(uow, actor, event_id)
            if not event.is_deletable:
                raise InvalidTransitionError(event.status.value, "delete")
            await uow.events.delete(event.id)
            await uow.commit()
