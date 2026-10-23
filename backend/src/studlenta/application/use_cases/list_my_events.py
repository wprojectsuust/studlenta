"""Сценарий: автор смотрит свои публикации и их статусы."""

from studlenta.application.dto import Actor, MyEventItem
from studlenta.application.ports import UnitOfWorkFactory
from studlenta.domain.events import EventStatus


class ListMyEvents:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def __call__(self, actor: Actor, status: EventStatus | None = None) -> list[MyEventItem]:
        async with self._uow() as uow:
            return await uow.queries.by_author(actor.user_id, status)
