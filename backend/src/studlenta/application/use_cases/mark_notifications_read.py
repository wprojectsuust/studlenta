"""Сценарий: отметить уведомления прочитанными (все или выбранные)."""

from collections.abc import Sequence
from uuid import UUID

from studlenta.application.dto import Actor
from studlenta.application.ports import Clock, UnitOfWorkFactory


class MarkNotificationsRead:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow, self._clock = uow, clock

    async def __call__(self, actor: Actor, ids: Sequence[UUID] | None) -> None:
        async with self._uow() as uow:
            await uow.notifications.mark_read(actor.user_id, ids, self._clock.now())
            await uow.commit()
