"""Сценарий: профиль текущего пользователя для шапки (имя, роль, непрочитанные)."""

from studlenta.application.dto import Actor, Profile
from studlenta.application.ports import UnitOfWorkFactory
from studlenta.domain.errors import AuthenticationError


class GetCurrentUser:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def __call__(self, actor: Actor) -> Profile:
        async with self._uow() as uow:
            user = await uow.users.get(actor.user_id)
            if user is None:
                raise AuthenticationError("Пользователь не найден")
            unread = await uow.notifications.count_unread(user.id)
        return Profile(user.id, user.email, user.full_name, user.role, unread, user.is_verified)
