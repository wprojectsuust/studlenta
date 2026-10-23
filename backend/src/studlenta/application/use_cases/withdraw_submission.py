"""Сценарий: автор отзывает заявку с модерации, чтобы поправить."""

from uuid import UUID

from studlenta.application.dto import Actor, ModerationAction, ModerationLogEntry
from studlenta.application.guards import load_own_event
from studlenta.application.ports import Clock, UnitOfWorkFactory


class WithdrawSubmission:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow, self._clock = uow, clock

    async def __call__(self, actor: Actor, event_id: UUID) -> None:
        now = self._clock.now()
        async with self._uow() as uow:
            event = await load_own_event(uow, actor, event_id)
            event.withdraw(now=now)
            await uow.events.update(event)
            await uow.moderation_log.add(
                ModerationLogEntry(event.id, actor.user_id, ModerationAction.WITHDRAWN, None, now)
            )
            await uow.commit()
