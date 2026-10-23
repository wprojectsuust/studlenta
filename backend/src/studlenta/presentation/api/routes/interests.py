"""Интересы: просмотры, подборка «Для вас», аналитика (ADR-0014)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from studlenta.application.use_cases.get_interest_analytics import GetInterestAnalytics
from studlenta.application.use_cases.list_recommendations import ListRecommendations
from studlenta.application.use_cases.record_event_view import RecordEventView
from studlenta.presentation.api.container import Deps
from studlenta.presentation.api.deps import CurrentActor, OptionalActor
from studlenta.presentation.api.schemas import InterestReportOut, RecommendedOut, ViewIn

router = APIRouter(tags=["Интересы"])


@router.post("/events/{event_id}/view", status_code=status.HTTP_204_NO_CONTENT)
async def record_view(event_id: UUID, body: ViewIn, c: Deps, viewer: OptionalActor) -> None:
    await RecordEventView(c.uow, c.clock, c.tz)(event_id, viewer, body.visitor_id)


@router.get("/recommendations")
async def recommendations(
    c: Deps,
    viewer: OptionalActor,
    visitor: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> list[RecommendedOut]:
    items = await ListRecommendations(c.uow, c.clock, c.tz)(viewer, visitor, limit)
    return [RecommendedOut.from_recommended(r) for r in items]


@router.get("/analytics/interests")
async def analytics(
    c: Deps, actor: CurrentActor, days: Annotated[int, Query(ge=1, le=365)] = 30
) -> InterestReportOut:
    return InterestReportOut.of(await GetInterestAnalytics(c.uow, c.clock, c.tz)(actor, days))
