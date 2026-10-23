"""Кабинет автора: черновики, отправка на модерацию, обложки, избранное, уведомления."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, UploadFile, status

from studlenta.application.use_cases.create_draft import CreateDraft
from studlenta.application.use_cases.delete_draft import DeleteDraft
from studlenta.application.use_cases.get_event_for_editing import GetEventForEditing
from studlenta.application.use_cases.list_my_events import ListMyEvents
from studlenta.application.use_cases.list_notifications import ListNotifications
from studlenta.application.use_cases.mark_notifications_read import MarkNotificationsRead
from studlenta.application.use_cases.submit_for_moderation import SubmitForModeration
from studlenta.application.use_cases.sync_guest_favorites import SyncGuestFavorites
from studlenta.application.use_cases.update_draft import UpdateDraft
from studlenta.application.use_cases.upload_cover import MAX_COVER_BYTES, UploadCover
from studlenta.application.use_cases.withdraw_submission import WithdrawSubmission
from studlenta.domain.errors import ValidationError
from studlenta.domain.events import EventContent, EventStatus
from studlenta.presentation.api.container import Container, Deps
from studlenta.presentation.api.deps import CurrentActor
from studlenta.presentation.api.schemas import (
    AddedOut,
    AuthoredEventOut,
    CreatedOut,
    EventIn,
    InboxOut,
    MarkReadIn,
    MyEventOut,
    NotificationOut,
    SyncFavoritesIn,
    UrlOut,
)

router = APIRouter(tags=["Мои публикации"])
NoContent = status.HTTP_204_NO_CONTENT


def _content(c: Container, body: EventIn) -> EventContent:
    # Обложка — только файл, загруженный через /uploads/cover: никаких внешних URL и javascript:.
    prefix = f"{c.settings.public_media_url}/covers/"
    if body.cover_url is not None and not (
        body.cover_url.startswith(prefix) and ".." not in body.cover_url
    ):
        raise ValidationError({"cover_url": "Загрузите обложку через форму"})
    return body.to_content()


@router.get("/me/events")
async def my_events(
    c: Deps, actor: CurrentActor, status: EventStatus | None = None
) -> list[MyEventOut]:
    items = await ListMyEvents(c.uow)(actor, status)
    return [MyEventOut(**{f: getattr(i, f) for f in MyEventOut.model_fields}) for i in items]


@router.post("/me/events", status_code=status.HTTP_201_CREATED)
async def create(body: EventIn, c: Deps, actor: CurrentActor) -> CreatedOut:
    return CreatedOut(id=await CreateDraft(c.uow, c.clock, c.ids)(actor, _content(c, body)))


@router.get("/me/events/{event_id}")
async def get_for_editing(event_id: UUID, c: Deps, actor: CurrentActor) -> AuthoredEventOut:
    return AuthoredEventOut.of(await GetEventForEditing(c.uow)(actor, event_id))


@router.put("/me/events/{event_id}", status_code=NoContent)
async def update(event_id: UUID, body: EventIn, c: Deps, actor: CurrentActor) -> None:
    await UpdateDraft(c.uow, c.clock)(actor, event_id, _content(c, body))


@router.delete("/me/events/{event_id}", status_code=NoContent)
async def delete(event_id: UUID, c: Deps, actor: CurrentActor) -> None:
    await DeleteDraft(c.uow)(actor, event_id)


@router.post("/me/events/{event_id}/submit", status_code=NoContent)
async def submit(event_id: UUID, c: Deps, actor: CurrentActor) -> None:
    await SubmitForModeration(c.uow, c.clock)(actor, event_id)


@router.post("/me/events/{event_id}/withdraw", status_code=NoContent)
async def withdraw(event_id: UUID, c: Deps, actor: CurrentActor) -> None:
    await WithdrawSubmission(c.uow, c.clock)(actor, event_id)


@router.post("/uploads/cover", status_code=status.HTTP_201_CREATED)
async def upload_cover(file: Annotated[UploadFile, File()], c: Deps, actor: CurrentActor) -> UrlOut:
    data = await file.read(MAX_COVER_BYTES + 1)
    return UrlOut(url=await UploadCover(c.storage, c.images, c.ids)(actor, data))


@router.post("/me/favorites/sync", tags=["Реакции"])
async def sync_favorites(body: SyncFavoritesIn, c: Deps, actor: CurrentActor) -> AddedOut:
    return AddedOut(added=await SyncGuestFavorites(c.uow, c.clock)(actor, body.event_ids))


@router.get("/me/notifications", tags=["Уведомления"])
async def notifications(c: Deps, actor: CurrentActor) -> InboxOut:
    inbox = await ListNotifications(c.uow)(actor)
    return InboxOut(
        items=[NotificationOut(id=n.id, kind=n.kind, event_id=n.event_id, text=n.text,
                               created_at=n.created_at, read_at=n.read_at) for n in inbox.items],
        unread=inbox.unread,
    )  # fmt: skip


@router.post("/me/notifications/read", status_code=NoContent, tags=["Уведомления"])
async def mark_read(body: MarkReadIn, c: Deps, actor: CurrentActor) -> None:
    await MarkNotificationsRead(c.uow, c.clock)(actor, body.ids)
