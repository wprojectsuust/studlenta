"""Сценарий: модератор одобряет заявку — событие появляется в ленте."""

from uuid import UUID

from studlenta.application.dto import Actor, ModerationAction, NotificationKind
from studlenta.application.use_cases._moderation import ModerationDecision


class ApproveEvent(ModerationDecision):
    action = ModerationAction.APPROVED
    kind = NotificationKind.APPROVED

    async def __call__(self, actor: Actor, event_id: UUID) -> None:
        now = self._clock.now()
        await self._decide(
            actor,
            event_id,
            None,
            apply=lambda e: e.approve(now=now),
            text=lambda e: f"Событие «{e.content.title}» опубликовано",
        )
