"""Кеш публичного чтения. Ключи и сроки — здесь, реализация — в инфраструктуре.

Кешируем только то, что одинаково для всех гостей: персональные флаги («лайкнул»,
«в избранном») и кабинеты в кеш не попадают.
"""

from collections.abc import Awaitable, Callable

from studlenta.application.ports import ReadCache

FEED_TTL = 15.0
EVENT_TTL = 30.0
CATEGORIES_TTL = 30.0
CALENDAR_TTL = 60.0


class NoCache:
    async def get_or_load[T](self, key: str, ttl: float, load: Callable[[], Awaitable[T]]) -> T:
        return await load()

    def invalidate(self, prefix: str = "") -> None:
        return None


NO_CACHE: ReadCache = NoCache()
