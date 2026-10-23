"""Публичная часть: лента, страница события, календарь, категории, реакции."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from studlenta.application.use_cases.add_to_favorites import AddToFavorites
from studlenta.application.use_cases.archive_event import ArchiveEvent
from studlenta.application.use_cases.get_calendar_month import GetCalendarMonth
from studlenta.application.use_cases.get_event_ics import GetEventIcs
from studlenta.application.use_cases.get_moderation_history import GetModerationHistory
from studlenta.application.use_cases.get_published_event import GetPublishedEvent
from studlenta.application.use_cases.like_event import LikeEvent
from studlenta.application.use_cases.list_categories import ListCategories
from studlenta.application.use_cases.list_events_by_day import ListEventsByDay
from studlenta.application.use_cases.list_published_events import FeedParams, ListPublishedEvents
from studlenta.application.use_cases.list_similar_events import ListSimilarEvents
from studlenta.application.use_cases.remove_from_favorites import RemoveFromFavorites
from studlenta.application.use_cases.unlike_event import UnlikeEvent
from studlenta.domain.periods import Period
from studlenta.presentation.api.container import Deps
from studlenta.presentation.api.deps import CurrentActor, OptionalActor
from studlenta.presentation.api.schemas import (
    CalendarDayOut,
    CategoryCountOut,
    CategoryOut,
    EventDetailsOut,
    FeedItemOut,
    HistoryOut,
    PageOut,
)

router = APIRouter(tags=["Лента"])
NoContent = status.HTTP_204_NO_CONTENT


@router.get("/events")
async def list_events(
    c: Deps,
    viewer: OptionalActor,
    period: Period = Period.ALL,
    category: str | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    favorites: bool = False,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> PageOut:
    params = FeedParams(period, category, q, favorites, cursor, limit)
    page = await ListPublishedEvents(c.uow, c.clock, c.tz, c.cache)(params, viewer)
    return PageOut(items=[FeedItemOut.of(i) for i in page.items], next_cursor=page.next_cursor)


@router.get("/events/{event_id}")
async def get_event(event_id: UUID, c: Deps, viewer: OptionalActor) -> EventDetailsOut:
    return EventDetailsOut.from_details(await GetPublishedEvent(c.uow, c.cache)(event_id, viewer))


@router.get("/events/{event_id}/similar")
async def similar(event_id: UUID, c: Deps, viewer: OptionalActor) -> list[FeedItemOut]:
    items = await ListSimilarEvents(c.uow, c.clock, c.tz)(event_id, viewer)
    return [FeedItemOut.of(i) for i in items]


@router.get(
    "/events/{event_id}/ics",
    response_class=Response,
    responses={200: {"content": {"text/calendar": {}}}},
)
async def ics(event_id: UUID, c: Deps) -> Response:
    return Response(
        await GetEventIcs(c.uow)(event_id),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="event-{event_id}.ics"'},
    )


@router.get("/events/{event_id}/history", tags=["Модерация"])
async def history(event_id: UUID, c: Deps, actor: CurrentActor) -> list[HistoryOut]:
    entries = await GetModerationHistory(c.uow)(actor, event_id)
    return [
        HistoryOut(action=e.action, note=e.note, created_at=e.created_at, actor_name=e.actor_name)
        for e in entries
    ]


@router.post("/events/{event_id}/archive", status_code=NoContent, tags=["Мои публикации"])
async def archive(event_id: UUID, c: Deps, actor: CurrentActor) -> None:
    await ArchiveEvent(c.uow, c.clock, c.cache)(actor, event_id)


@router.put("/events/{event_id}/like", status_code=NoContent, tags=["Реакции"])
async def like(event_id: UUID, c: Deps, actor: CurrentActor) -> None:
    await LikeEvent(c.uow, c.clock)(actor, event_id)


@router.delete("/events/{event_id}/like", status_code=NoContent, tags=["Реакции"])
async def unlike(event_id: UUID, c: Deps, actor: CurrentActor) -> None:
    await UnlikeEvent(c.uow)(actor, event_id)


@router.put("/events/{event_id}/favorite", status_code=NoContent, tags=["Реакции"])
async def favorite(event_id: UUID, c: Deps, actor: CurrentActor) -> None:
    await AddToFavorites(c.uow, c.clock)(actor, event_id)


@router.delete("/events/{event_id}/favorite", status_code=NoContent, tags=["Реакции"])
async def unfavorite(event_id: UUID, c: Deps, actor: CurrentActor) -> None:
    await RemoveFromFavorites(c.uow)(actor, event_id)


@router.get("/categories")
async def categories(c: Deps) -> list[CategoryCountOut]:
    return [
        CategoryCountOut(**CategoryOut.of(x.category).model_dump(), upcoming_count=x.upcoming_count)
        for x in await ListCategories(c.uow, c.clock, c.tz, c.cache)()
    ]


@router.get("/calendar", tags=["Календарь"])
async def calendar(
    c: Deps, month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$", examples=["2026-10"])]
) -> list[CalendarDayOut]:
    year, mon = (int(p) for p in month.split("-"))
    days = await GetCalendarMonth(c.uow, c.tz, c.cache)(year, mon)
    return [CalendarDayOut.of(d) for d in days]


@router.get("/calendar/day", tags=["Календарь"])
async def calendar_day(
    c: Deps, viewer: OptionalActor, day: Annotated[date, Query(alias="date")]
) -> list[FeedItemOut]:
    return [FeedItemOut.of(i) for i in await ListEventsByDay(c.uow, c.tz)(day, viewer)]
