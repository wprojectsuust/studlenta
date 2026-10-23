"""Сценарий: «Добавить в календарь» — файл .ics для опубликованного события."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from studlenta.application.ports import UnitOfWorkFactory
from studlenta.domain.errors import NotFoundError

DEFAULT_DURATION = timedelta(hours=1)


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


class GetEventIcs:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def __call__(self, event_id: UUID) -> str:
        async with self._uow() as uow:
            details = await uow.queries.published(event_id, None)
        if details is None:
            raise NotFoundError("Событие")
        item = details.item
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//UUST//Studlenta//RU",
            "BEGIN:VEVENT",
            f"UID:{item.id}@studlenta",
            f"DTSTAMP:{_stamp(details.published_at)}",
            f"DTSTART:{_stamp(item.starts_at)}",
            f"DTEND:{_stamp(item.ends_at or item.starts_at + DEFAULT_DURATION)}",
            f"SUMMARY:{_escape(item.title)}",
            f"LOCATION:{_escape(item.place)}",
            f"DESCRIPTION:{_escape(details.body)}",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
        return "\r\n".join(lines) + "\r\n"
