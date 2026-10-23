"""Сценарий: страница опубликованного события."""

from uuid import UUID

from studlenta.application.caching import EVENT_TTL, NO_CACHE
from studlenta.application.dto import Actor, EventDetails
from studlenta.application.ports import ReadCache, UnitOfWorkFactory
from studlenta.domain.errors import NotFoundError


class GetPublishedEvent:
    def __init__(self, uow: UnitOfWorkFactory, cache: ReadCache = NO_CACHE) -> None:
        self._uow, self._cache = uow, cache

    async def __call__(self, event_id: UUID, viewer: Actor | None) -> EventDetails:
        async def load() -> EventDetails | None:
            async with self._uow() as uow:
                return await uow.queries.published(event_id, viewer.user_id if viewer else None)

        details = (
            await self._cache.get_or_load(f"event:{event_id}", EVENT_TTL, load)
            if viewer is None
            else await load()
        )
        if details is None:
            raise NotFoundError("Событие")
        return details
