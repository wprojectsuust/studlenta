"""Сценарий: автор отправляет событие на предмодерацию."""

from uuid import UUID

from studlenta.application.dto import Actor, ModerationAction, ModerationLogEntry
from studlenta.application.guards import load_own_event
from studlenta.application.ports import Clock, UnitOfWorkFactory
from studlenta.domain.errors import PermissionDeniedError

NOT_VERIFIED = "Подтвердите почту, чтобы отправлять события на модерацию — ссылка в письме"


class SubmitForModeration:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow, self._clock = uow, clock

    async def __call__(self, actor: Actor, event_id: UUID) -> None:
        now = self._clock.now()
        async with self._uow() as uow:
            event = await load_own_event(uow, actor, event_id)
            author = await uow.users.get(actor.user_id)
            if author is None or not author.is_verified:
                raise PermissionDeniedError(NOT_VERIFIED)
            event.submit(now=now)
            await uow.events.update(event)
            await uow.moderation_log.add(
                ModerationLogEntry(event.id, actor.user_id, ModerationAction.SUBMITTED, None, now)
            )
            await uow.commit()
