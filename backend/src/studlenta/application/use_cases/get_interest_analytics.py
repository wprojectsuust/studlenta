"""Сценарий: аналитика интересов. Модератор видит всю ленту, автор — свои события."""

from datetime import timedelta, tzinfo

from studlenta.application.dto import Actor, InterestReport
from studlenta.application.ports import Clock, UnitOfWorkFactory
from studlenta.domain.errors import ValidationError

MAX_DAYS = 365


class GetInterestAnalytics:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock, tz: tzinfo) -> None:
        self._uow, self._clock, self._tz = uow, clock, tz

    async def __call__(self, actor: Actor, days: int = 30) -> InterestReport:
        if not 1 <= days <= MAX_DAYS:
            raise ValidationError({"days": f"От 1 до {MAX_DAYS} дней"})
        now = self._clock.now()
        author_id = None if actor.role.can_moderate else actor.user_id
        async with self._uow() as uow:
            return await uow.interests.report(now - timedelta(days=days), now, self._tz, author_id)
