from uuid import UUID

from fastapi import APIRouter, status

from studlenta.application.use_cases.approve_event import ApproveEvent
from studlenta.application.use_cases.list_moderation_queue import ListModerationQueue
from studlenta.application.use_cases.reject_event import RejectEvent
from studlenta.application.use_cases.request_changes import RequestChanges
from studlenta.domain.events import EventStatus
from studlenta.presentation.api.container import Deps
from studlenta.presentation.api.deps import CurrentActor
from studlenta.presentation.api.schemas import AuthoredEventOut, NoteIn

router = APIRouter(prefix="/moderation", tags=["Модерация"])
NoContent = status.HTTP_204_NO_CONTENT


@router.get("/queue")
async def queue(
    c: Deps, actor: CurrentActor, status: EventStatus = EventStatus.PENDING
) -> list[AuthoredEventOut]:
    return [AuthoredEventOut.of(e) for e in await ListModerationQueue(c.uow)(actor, status)]


@router.post("/events/{event_id}/approve", status_code=NoContent)
async def approve(event_id: UUID, c: Deps, actor: CurrentActor) -> None:
    await ApproveEvent(c.uow, c.clock, c.ids, c.cache)(actor, event_id)


@router.post("/events/{event_id}/request-changes", status_code=NoContent)
async def request_changes(event_id: UUID, body: NoteIn, c: Deps, actor: CurrentActor) -> None:
    await RequestChanges(c.uow, c.clock, c.ids)(actor, event_id, body.note)


@router.post("/events/{event_id}/reject", status_code=NoContent)
async def reject(event_id: UUID, body: NoteIn, c: Deps, actor: CurrentActor) -> None:
    await RejectEvent(c.uow, c.clock, c.ids)(actor, event_id, body.note)
