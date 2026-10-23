"""Сценарий: страница опубликованного события."""

from uuid import UUID

from studlenta.application.dto import Actor, EventDetails
from studlenta.application.ports import UnitOfWorkFactory
from studlenta.domain.errors import NotFoundError


class GetPublishedEvent:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def __call__(self, event_id: UUID, viewer: Actor | None) -> EventDetails:
        async with self._uow() as uow:
            details = await uow.queries.published(event_id, viewer.user_id if viewer else None)
        if details is None:
            raise NotFoundError("Событие")
        return details
