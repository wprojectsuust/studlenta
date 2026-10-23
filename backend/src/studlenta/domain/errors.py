"""Ошибки предметной области. Слой presentation переводит их в HTTP-коды."""

from collections.abc import Mapping


class DomainError(Exception):
    """База для всех ожидаемых ошибок бизнес-логики."""


class ValidationError(DomainError):
    """Данные не проходят правила. ``fields`` — поле → человекочитаемая причина."""

    def __init__(self, fields: Mapping[str, str]) -> None:
        self.fields = dict(fields)
        super().__init__("; ".join(f"{k}: {v}" for k, v in self.fields.items()))


class InvalidTransitionError(DomainError):
    """Действие недопустимо в текущем статусе."""

    def __init__(self, current: str, action: str) -> None:
        self.current = current
        self.action = action
        super().__init__(f"Нельзя выполнить «{action}» в статусе «{current}»")


class NotFoundError(DomainError):
    def __init__(self, entity: str) -> None:
        self.entity = entity
        super().__init__(f"{entity} не найдено")


class PermissionDeniedError(DomainError):
    pass


class ConflictError(DomainError):
    """Состояние изменилось параллельно (например, заявку уже обработал другой модератор)."""


class AuthenticationError(DomainError):
    pass
