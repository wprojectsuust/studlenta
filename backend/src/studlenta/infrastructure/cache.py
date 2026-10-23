"""Кеш чтения в памяти процесса: TTL + LRU + один запрос в базу на ключ при параллельных промахах.

Одна реплика API (ADR-0010) — внешний Redis не нужен. При нескольких репликах кеш станет
локальным для каждой; сброс по событиям тогда нужно будет рассылать (ADR-0013).
"""

import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Any, cast


class TtlCache:
    def __init__(self, max_entries: int = 512, now: Callable[[], float] = time.monotonic) -> None:
        self._max, self._now = max_entries, now
        self._data: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._inflight: dict[str, asyncio.Future[Any]] = {}
        self._generation = 0

    def __len__(self) -> int:
        return len(self._data)

    async def get_or_load[T](self, key: str, ttl: float, load: Callable[[], Awaitable[T]]) -> T:
        hit = self._data.get(key)
        if hit is not None and hit[0] > self._now():
            self._data.move_to_end(key)
            return cast(T, hit[1])
        if (pending := self._inflight.get(key)) is not None:
            return cast(T, await asyncio.shield(pending))

        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._inflight[key] = future
        generation = self._generation
        try:
            value = await load()
        except BaseException as exc:
            future.set_exception(exc)
            future.exception()  # ждущих может не быть — не шумим «exception was never retrieved»
            raise
        finally:
            self._inflight.pop(key, None)
        future.set_result(value)
        # Сброс во время загрузки (например, одобрили событие) — устаревший результат не кешируем.
        if generation == self._generation:
            self._data[key] = (self._now() + ttl, value)
            self._data.move_to_end(key)
            while len(self._data) > self._max:
                self._data.popitem(last=False)
        return value

    def invalidate(self, prefix: str = "") -> None:
        self._generation += 1
        for key in [k for k in self._data if k.startswith(prefix)]:
            del self._data[key]
