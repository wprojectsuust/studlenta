"""Сценарий: модератор возвращает заявку автору с комментарием."""

from uuid import UUID

from studlenta.application.dto import Actor, ModerationAction, NotificationKind
from studlenta.application.use_cases._moderation import ModerationDecision


class RequestChanges(ModerationDecision):
    action = ModerationAction.CHANGES_REQUESTED
    kind = NotificationKind.CHANGES_REQUESTED

    async def __call__(self, actor: Actor, event_id: UUID, note: str) -> None:
        now = self._clock.now()
        await self._decide(
            actor,
            event_id,
            note.strip(),
            apply=lambda e: e.request_changes(note=note, now=now),
            text=lambda e: f"Событие «{e.content.title}» нужно поправить: {e.moderator_note}",
        )
