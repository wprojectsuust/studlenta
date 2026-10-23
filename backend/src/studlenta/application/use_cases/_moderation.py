"""Общий шаг для решений модератора: переход, журнал, уведомление автору — одной транзакцией."""

from collections.abc import Callable
from uuid import UUID

from studlenta.application.caching import NO_CACHE
from studlenta.application.dto import (
    Actor,
    ModerationAction,
    ModerationLogEntry,
    Notification,
    NotificationKind,
)
from studlenta.application.guards import load_event, require_moderator
from studlenta.application.ports import Clock, IdGenerator, ReadCache, UnitOfWorkFactory
from studlenta.domain.errors import PermissionDeniedError
from studlenta.domain.events import Event


class ModerationDecision:
    action: ModerationAction
    kind: NotificationKind
    changes_public_feed = False  # одобрение меняет публичную ленту — сбрасываем кеш

    def __init__(
        self, uow: UnitOfWorkFactory, clock: Clock, ids: IdGenerator, cache: ReadCache = NO_CACHE
    ) -> None:
        self._uow, self._clock, self._ids, self._cache = uow, clock, ids, cache

    async def _decide(
        self,
        actor: Actor,
        event_id: UUID,
        note: str | None,
        apply: Callable[[Event], None],
        text: Callable[[Event], str],
    ) -> None:
        require_moderator(actor)
        now = self._clock.now()
        async with self._uow() as uow:
            event = await load_event(uow, event_id)
            if event.author_id == actor.user_id:
                raise PermissionDeniedError("Нельзя модерировать своё событие")
            apply(event)
            await uow.events.update(event)
            await uow.moderation_log.add(
                ModerationLogEntry(event.id, actor.user_id, self.action, note, now)
            )
            await uow.notifications.add(
                Notification(
                    self._ids.new_id(), event.author_id, self.kind, event.id, text(event), now
                )
            )
            await uow.commit()
        if self.changes_public_feed:
            self._cache.invalidate()
