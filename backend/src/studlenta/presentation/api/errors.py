"""Единый формат ошибок: ``{"error": {"code", "message", "fields"}}``."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from studlenta.domain.errors import (
    AuthenticationError,
    ConflictError,
    DomainError,
    InvalidTransitionError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from studlenta.presentation.api.rate_limit import TooManyAttemptsError

_STATUS: list[tuple[type[DomainError], int, str]] = [
    (ValidationError, 422, "validation_error"),
    (AuthenticationError, 401, "unauthorized"),
    (PermissionDeniedError, 403, "forbidden"),
    (NotFoundError, 404, "not_found"),
    (InvalidTransitionError, 409, "invalid_transition"),
    (ConflictError, 409, "conflict"),
]


def error_response(
    status: int, code: str, message: str, fields: dict[str, str] | None = None
) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    body = {"error": {"code": code, "message": message, "fields": fields or {}}}
    return JSONResponse(body, status_code=status, headers=headers)


async def _domain(_: Request, exc: Exception) -> JSONResponse:
    for kind, status, code in _STATUS:
        if isinstance(exc, kind):
            fields = exc.fields if isinstance(exc, ValidationError) else None
            message = "Проверьте поля формы" if fields else str(exc)
            return error_response(status, code, message, fields)
    return error_response(400, "domain_error", str(exc))


async def _request_validation(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):  # pragma: no cover - регистрация ниже
        raise exc
    fields: dict[str, str] = {}
    for err in exc.errors():
        loc = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
        fields[".".join(loc) or "request"] = err["msg"]
    return error_response(422, "validation_error", "Некорректный запрос", fields)


async def _too_many(_: Request, exc: Exception) -> JSONResponse:
    return error_response(429, "too_many_attempts", "Слишком много попыток, подождите минуту")


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(TooManyAttemptsError, _too_many)
    app.add_exception_handler(DomainError, _domain)
    app.add_exception_handler(RequestValidationError, _request_validation)
