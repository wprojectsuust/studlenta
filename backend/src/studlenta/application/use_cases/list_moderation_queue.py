"""Сценарий: модератор открывает очередь (или одобренные / отклонённые)."""

from studlenta.application.dto import Actor, AuthoredEvent
from studlenta.application.guards import require_moderator
from studlenta.application.ports import UnitOfWorkFactory
from studlenta.domain.errors import ValidationError
from studlenta.domain.events import EventStatus

QUEUE_STATUSES = frozenset(
    {
        EventStatus.PENDING,
        EventStatus.CHANGES_REQUESTED,
        EventStatus.PUBLISHED,
        EventStatus.REJECTED,
    }
)


class ListModerationQueue:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def __call__(
        self, actor: Actor, status: EventStatus = EventStatus.PENDING
    ) -> list[AuthoredEvent]:
        require_moderator(actor)
        if status not in QUEUE_STATUSES:
            raise ValidationError({"status": "Недоступный для модерации статус"})
        async with self._uow() as uow:
            return await uow.queries.moderation_queue(status)
