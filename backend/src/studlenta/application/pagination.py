"""Курсор keyset-пагинации: непрозрачная для клиента строка из (starts_at, id)."""

import base64
import binascii
from datetime import datetime
from uuid import UUID

from studlenta.domain.errors import ValidationError


def encode_cursor(starts_at: datetime, event_id: UUID) -> str:
    raw = f"{starts_at.isoformat()}|{event_id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        stamp, event_id = base64.urlsafe_b64decode(padded).decode().split("|")
        starts_at = datetime.fromisoformat(stamp)
        if starts_at.tzinfo is None:
            raise ValueError("naive")
        return starts_at, UUID(event_id)
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise ValidationError({"cursor": "Некорректный курсор страницы"}) from exc
