"""Сценарий: просмотр страницы события — сигнал интереса для рекомендаций и аналитики."""

from datetime import tzinfo
from uuid import UUID

from studlenta.application.dto import Actor
from studlenta.application.ports import Clock, UnitOfWorkFactory
from studlenta.domain.errors import ValidationError


def viewer_keys(viewer: Actor | None, visitor_id: UUID | None) -> list[str]:
    """Ключи зрителя: аккаунт и/или анонимный id браузера (без персональных данных)."""
    keys = [f"u:{viewer.user_id}"] if viewer else []
    return keys + ([f"g:{visitor_id}"] if visitor_id else [])


class RecordEventView:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock, tz: tzinfo) -> None:
        self._uow, self._clock, self._tz = uow, clock, tz

    async def __call__(self, event_id: UUID, viewer: Actor | None, visitor_id: UUID | None) -> None:
        keys = viewer_keys(viewer, visitor_id)
        if not keys:
            raise ValidationError({"visitor_id": "Нужен id посетителя или вход"})
        now = self._clock.now()
        async with self._uow() as uow:
            # Вошедший считается по аккаунту: так просмотр с телефона и ноутбука — один.
            user_id = viewer.user_id if viewer else None
            if await uow.interests.record_view(
                event_id, keys[0], user_id, now.astimezone(self._tz).date(), now
            ):
                await uow.commit()
