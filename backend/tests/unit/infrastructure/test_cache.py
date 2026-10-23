import asyncio

import pytest

from studlenta.infrastructure.cache import TtlCache


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def clock() -> Clock:
    return Clock()


def loader(calls: list[str], value: str):  # type: ignore[no-untyped-def]
    async def load() -> str:
        calls.append(value)
        return value

    return load


async def test_hit_within_ttl_and_reload_after(clock: Clock) -> None:
    cache = TtlCache(max_entries=10, now=clock)
    calls: list[str] = []
    assert await cache.get_or_load("k", 30, loader(calls, "a")) == "a"
    clock.t = 29
    assert await cache.get_or_load("k", 30, loader(calls, "b")) == "a"
    clock.t = 31
    assert await cache.get_or_load("k", 30, loader(calls, "c")) == "c"
    assert calls == ["a", "c"]


async def test_least_recently_used_is_evicted(clock: Clock) -> None:
    cache = TtlCache(max_entries=2, now=clock)
    calls: list[str] = []
    await cache.get_or_load("a", 60, loader(calls, "a"))
    await cache.get_or_load("b", 60, loader(calls, "b"))
    await cache.get_or_load("a", 60, loader(calls, "x"))  # a свежее
    await cache.get_or_load("c", 60, loader(calls, "c"))  # вытесняет b
    await cache.get_or_load("b", 60, loader(calls, "b2"))
    assert calls == ["a", "b", "c", "b2"]
    assert len(cache) == 2


async def test_invalidate_by_prefix(clock: Clock) -> None:
    cache = TtlCache(max_entries=10, now=clock)
    calls: list[str] = []
    for key in ("feed:1", "feed:2", "categories"):
        await cache.get_or_load(key, 60, loader(calls, key))
    cache.invalidate("feed:")
    await cache.get_or_load("feed:1", 60, loader(calls, "feed:1*"))
    await cache.get_or_load("categories", 60, loader(calls, "never"))
    assert calls == ["feed:1", "feed:2", "categories", "feed:1*"]
    cache.invalidate()
    assert len(cache) == 0


async def test_concurrent_misses_load_once(clock: Clock) -> None:
    cache = TtlCache(max_entries=10, now=clock)
    started = 0

    async def slow() -> int:
        nonlocal started
        started += 1
        await asyncio.sleep(0.01)
        return 42

    results = await asyncio.gather(*(cache.get_or_load("k", 60, slow) for _ in range(20)))
    assert results == [42] * 20
    assert started == 1


async def test_errors_are_not_cached(clock: Clock) -> None:
    cache = TtlCache(max_entries=10, now=clock)

    async def boom() -> str:
        raise RuntimeError("БД недоступна")

    with pytest.raises(RuntimeError):
        await cache.get_or_load("k", 60, boom)
    calls: list[str] = []
    assert await cache.get_or_load("k", 60, loader(calls, "ok")) == "ok"


async def test_invalidation_during_load_is_respected(clock: Clock) -> None:
    """Если событие одобрили, пока шёл запрос, устаревший результат не должен осесть в кеше."""
    cache = TtlCache(max_entries=10, now=clock)

    async def stale() -> str:
        cache.invalidate()
        return "stale"

    assert await cache.get_or_load("k", 60, stale) == "stale"
    calls: list[str] = []
    assert await cache.get_or_load("k", 60, loader(calls, "fresh")) == "fresh"
