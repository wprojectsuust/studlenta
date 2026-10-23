"""Сценарий: модератор отклоняет заявку с указанием причины."""

from uuid import UUID

from studlenta.application.dto import Actor, ModerationAction, NotificationKind
from studlenta.application.use_cases._moderation import ModerationDecision


class RejectEvent(ModerationDecision):
    action = ModerationAction.REJECTED
    kind = NotificationKind.REJECTED

    async def __call__(self, actor: Actor, event_id: UUID, note: str) -> None:
        now = self._clock.now()
        await self._decide(
            actor,
            event_id,
            note.strip(),
            apply=lambda e: e.reject(note=note, now=now),
            text=lambda e: f"Событие «{e.content.title}» отклонено: {e.moderator_note}",
        )
