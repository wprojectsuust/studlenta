"""Сценарий (фоновый, запускается по расписанию): напомнить о событиях из избранного.

Напоминание приходит один раз, когда до начала остаётся меньше суток.
"""

from datetime import timedelta

from studlenta.application.dto import Notification, NotificationKind
from studlenta.application.ports import Clock, IdGenerator, UnitOfWorkFactory

WINDOW = timedelta(days=1)


class SendFavoriteReminders:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock, ids: IdGenerator) -> None:
        self._uow, self._clock, self._ids = uow, clock, ids

    async def __call__(self) -> int:
        now = self._clock.now()
        sent = 0
        async with self._uow() as uow:
            for user_id, event_id, title in await uow.reactions.favorites_starting_between(
                now, now + WINDOW
            ):
                note = Notification(
                    self._ids.new_id(),
                    user_id,
                    NotificationKind.REMINDER,
                    event_id,
                    f"Из избранного скоро начнётся «{title}»",
                    now,
                )
                sent += await uow.notifications.add(note)
            await uow.commit()
        return sent
