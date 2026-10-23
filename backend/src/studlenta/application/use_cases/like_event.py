"""Сценарий: поставить лайк опубликованному событию."""

from uuid import UUID

from studlenta.application.dto import Actor
from studlenta.application.ports import Clock, UnitOfWorkFactory
from studlenta.application.use_cases._reactions import ensure_published


class LikeEvent:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow, self._clock = uow, clock

    async def __call__(self, actor: Actor, event_id: UUID) -> None:
        async with self._uow() as uow:
            await ensure_published(uow, event_id)
            await uow.reactions.like(actor.user_id, event_id, self._clock.now())
            await uow.commit()
