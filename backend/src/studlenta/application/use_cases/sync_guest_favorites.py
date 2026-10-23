"""Сценарий: после входа перенести избранное гостя (из localStorage) в аккаунт."""

from collections.abc import Sequence
from uuid import UUID

from studlenta.application.dto import Actor
from studlenta.application.ports import Clock, UnitOfWorkFactory
from studlenta.domain.errors import ValidationError

MAX_SYNC = 200


class SyncGuestFavorites:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow, self._clock = uow, clock

    async def __call__(self, actor: Actor, event_ids: Sequence[UUID]) -> int:
        if len(event_ids) > MAX_SYNC:
            raise ValidationError({"event_ids": f"Не больше {MAX_SYNC} событий за раз"})
        now = self._clock.now()
        async with self._uow() as uow:
            published = await uow.reactions.published_ids(list(dict.fromkeys(event_ids)))
            for event_id in published:
                await uow.reactions.favorite(actor.user_id, event_id, now)
            await uow.commit()
        return len(published)
