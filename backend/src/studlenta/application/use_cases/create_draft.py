"""Сценарий: автор начинает новое событие (черновик)."""

from uuid import UUID

from studlenta.application.dto import Actor
from studlenta.application.ports import Clock, IdGenerator, UnitOfWork, UnitOfWorkFactory
from studlenta.domain.errors import ValidationError
from studlenta.domain.events import Event, EventContent


async def ensure_category(uow: UnitOfWork, content: EventContent) -> None:
    if content.category_id is not None and await uow.categories.get(content.category_id) is None:
        raise ValidationError({"category_id": "Такой категории нет"})


class CreateDraft:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock, ids: IdGenerator) -> None:
        self._uow, self._clock, self._ids = uow, clock, ids

    async def __call__(self, actor: Actor, content: EventContent) -> UUID:
        async with self._uow() as uow:
            await ensure_category(uow, content)
            event = Event.create_draft(
                event_id=self._ids.new_id(),
                author_id=actor.user_id,
                content=content,
                now=self._clock.now(),
            )
            await uow.events.add(event)
            await uow.commit()
            return event.id
