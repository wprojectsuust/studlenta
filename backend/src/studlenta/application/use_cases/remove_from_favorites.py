"""Сценарий: убрать событие из избранного."""

from uuid import UUID

from studlenta.application.dto import Actor
from studlenta.application.ports import UnitOfWorkFactory


class RemoveFromFavorites:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def __call__(self, actor: Actor, event_id: UUID) -> None:
        async with self._uow() as uow:
            await uow.reactions.unfavorite(actor.user_id, event_id)
            await uow.commit()
