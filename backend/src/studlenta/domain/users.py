import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from studlenta.domain.errors import ValidationError

PASSWORD_MIN, PASSWORD_MAX = 8, 128
NAME_MAX = 120
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Role(StrEnum):
    AUTHOR = "author"
    MODERATOR = "moderator"
    ADMIN = "admin"

    @property
    def can_moderate(self) -> bool:
        return self in (Role.MODERATOR, Role.ADMIN)


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    email: str
    full_name: str
    role: Role
    password_hash: str
    created_at: datetime


def normalize_email(raw: str) -> str:
    email = raw.strip().lower()
    if not _EMAIL.match(email):
        raise ValidationError({"email": "Проверьте адрес почты"})
    return email


def validate_password(raw: str) -> None:
    if len(raw) < PASSWORD_MIN:
        raise ValidationError({"password": f"Минимум {PASSWORD_MIN} символов"})
    if len(raw) > PASSWORD_MAX:
        raise ValidationError({"password": f"Не длиннее {PASSWORD_MAX} символов"})


def normalize_name(raw: str) -> str:
    name = " ".join(raw.split())
    if not name:
        raise ValidationError({"full_name": "Укажите имя"})
    if len(name) > NAME_MAX:
        raise ValidationError({"full_name": f"Не длиннее {NAME_MAX} символов"})
    return name
