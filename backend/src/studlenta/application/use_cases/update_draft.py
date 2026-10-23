"""Сценарий: автор правит черновик или событие, возвращённое на доработку."""

from uuid import UUID

from studlenta.application.dto import Actor
from studlenta.application.guards import load_own_event
from studlenta.application.ports import Clock, UnitOfWorkFactory
from studlenta.application.use_cases.create_draft import ensure_category
from studlenta.domain.events import EventContent


class UpdateDraft:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow, self._clock = uow, clock

    async def __call__(self, actor: Actor, event_id: UUID, content: EventContent) -> None:
        async with self._uow() as uow:
            event = await load_own_event(uow, actor, event_id)
            await ensure_category(uow, content)
            event.edit(content, now=self._clock.now())
            await uow.events.update(event)
            await uow.commit()
