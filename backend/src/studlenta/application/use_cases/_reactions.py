from uuid import UUID

from studlenta.application.ports import UnitOfWork
from studlenta.domain.errors import NotFoundError


async def ensure_published(uow: UnitOfWork, event_id: UUID) -> None:
    if event_id not in await uow.reactions.published_ids([event_id]):
        raise NotFoundError("Событие")
