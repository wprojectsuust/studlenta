"""Сценарий: история решений по событию — для автора и модераторов."""

from uuid import UUID

from studlenta.application.dto import Actor, ModerationLogEntry
from studlenta.application.guards import load_event
from studlenta.application.ports import UnitOfWorkFactory
from studlenta.domain.errors import PermissionDeniedError


class GetModerationHistory:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def __call__(self, actor: Actor, event_id: UUID) -> list[ModerationLogEntry]:
        async with self._uow() as uow:
            event = await load_event(uow, event_id)
            if event.author_id != actor.user_id and not actor.role.can_moderate:
                raise PermissionDeniedError("История доступна автору и модераторам")
            return await uow.moderation_log.list_for_event(event_id)
