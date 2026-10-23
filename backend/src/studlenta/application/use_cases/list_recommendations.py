"""Сценарий: подборка «Для вас» с объяснением, почему событие предложено (ADR-0014)."""

from datetime import timedelta, tzinfo
from uuid import UUID

from studlenta.application.dto import Actor, CandidateItem, RecommendedItem
from studlenta.application.ports import Clock, UnitOfWorkFactory
from studlenta.application.use_cases.record_event_view import viewer_keys
from studlenta.domain.periods import Period, period_bounds
from studlenta.domain.recommendations import Candidate, Reason, ReasonKind, recommend

HISTORY_WINDOW = timedelta(days=180)
POPULARITY_WINDOW = timedelta(days=14)
CANDIDATES = 200


class ListRecommendations:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock, tz: tzinfo) -> None:
        self._uow, self._clock, self._tz = uow, clock, tz

    async def __call__(
        self, viewer: Actor | None, visitor_id: UUID | None, limit: int = 10
    ) -> list[RecommendedItem]:
        now = self._clock.now()
        start, _ = period_bounds(Period.ALL, now=now, tz=self._tz)
        keys = viewer_keys(viewer, visitor_id)
        user_id = viewer.user_id if viewer else None
        async with self._uow() as uow:
            pool = await uow.interests.candidates(
                start, user_id, now - POPULARITY_WINDOW, CANDIDATES
            )
            history = (
                await uow.interests.history(keys, user_id, now - HISTORY_WINDOW) if keys else []
            )
            seeds = list(dict.fromkeys(h.interaction.event_id for h in history))
            co_views = (
                await uow.interests.co_views(seeds, keys, now - HISTORY_WINDOW) if seeds else []
            )
        by_id = {c.item.id: c for c in pool}
        ranked = recommend(
            [h.interaction for h in history],
            [Candidate(c.item.id, c.item.category.id, c.lexemes, c.popularity) for c in pool],
            co_views,
            now,
            limit,
        )
        titles = {h.interaction.event_id: h.title for h in history}
        return [
            RecommendedItem(
                by_id[r.event_id].item,
                _explain(r.reason, by_id[r.event_id], titles),
                r.reason.kind.value,
            )
            for r in ranked
        ]


def _explain(reason: Reason, c: CandidateItem, titles: dict[UUID, str]) -> str:
    seen = titles.get(reason.ref, "") if isinstance(reason.ref, UUID) else ""
    match reason.kind:
        case ReasonKind.CATEGORY:
            return f"Вы часто смотрите «{c.item.category.name}»"
        case ReasonKind.SIMILAR:
            return f"Похоже на «{seen}»"
        case ReasonKind.ALSO_VIEWED:
            return f"Смотрели те, кто смотрел «{seen}»"
        case ReasonKind.POPULAR:
            return "Популярно у студентов"
        case _:
            return "Скоро"
