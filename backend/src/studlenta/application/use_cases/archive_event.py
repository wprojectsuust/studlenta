"""Сценарий: снять опубликованное событие с ленты (автор или модератор)."""

from uuid import UUID

from studlenta.application.dto import Actor, ModerationAction, ModerationLogEntry
from studlenta.application.guards import load_event
from studlenta.application.ports import Clock, UnitOfWorkFactory
from studlenta.domain.errors import PermissionDeniedError


class ArchiveEvent:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow, self._clock = uow, clock

    async def __call__(self, actor: Actor, event_id: UUID) -> None:
        now = self._clock.now()
        async with self._uow() as uow:
            event = await load_event(uow, event_id)
            if event.author_id != actor.user_id and not actor.role.can_moderate:
                raise PermissionDeniedError("Снять с публикации может автор или модератор")
            event.archive(now=now)
            await uow.events.update(event)
            await uow.moderation_log.add(
                ModerationLogEntry(event.id, actor.user_id, ModerationAction.ARCHIVED, None, now)
            )
            await uow.commit()
