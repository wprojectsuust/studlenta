"""Простое ограничение неудачных входов (в памяти процесса — достаточно для одной реплики).

Для нескольких реплик счётчик нужно вынести в Redis — см. ADR-0006.
"""

import time
from collections import defaultdict, deque


class TooManyAttemptsError(Exception):
    """Превышен лимит неудачных попыток — отвечаем 429."""


class FailureLimiter:
    def __init__(self, max_failures: int, window_seconds: float) -> None:
        self._max, self._window = max_failures, window_seconds
        self._failures: defaultdict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        hits = self._failures[key]
        while hits and now - hits[0] > self._window:
            hits.popleft()
        return hits

    def is_blocked(self, key: str) -> bool:
        return len(self._prune(key, time.monotonic())) >= self._max

    def register_failure(self, key: str) -> None:
        self._prune(key, time.monotonic()).append(time.monotonic())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
