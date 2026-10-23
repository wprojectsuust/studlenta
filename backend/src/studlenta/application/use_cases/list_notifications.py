"""Сценарий: колокольчик — последние уведомления и число непрочитанных."""

from datetime import datetime

from studlenta.application.dto import Actor, Inbox
from studlenta.application.ports import UnitOfWorkFactory

PAGE = 20


class ListNotifications:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def __call__(self, actor: Actor, before: datetime | None = None) -> Inbox:
        async with self._uow() as uow:
            items = await uow.notifications.list_for_user(actor.user_id, PAGE, before)
            unread = await uow.notifications.count_unread(actor.user_id)
        return Inbox(items=items, unread=unread)
