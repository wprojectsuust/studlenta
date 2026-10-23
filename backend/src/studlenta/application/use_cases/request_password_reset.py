"""Сценарий: «Забыли пароль?» — письмо со ссылкой на смену пароля.

Ответ всегда одинаковый: по нему нельзя узнать, зарегистрирована ли почта.
"""

import logging
from datetime import timedelta

from studlenta.application.dto import EmailMessage, PasswordResetRecord
from studlenta.application.emails import letter
from studlenta.application.ports import Clock, EmailSender, TokenService, UnitOfWorkFactory
from studlenta.domain.errors import ValidationError
from studlenta.domain.users import normalize_email

RESET_TTL = timedelta(hours=1)
RESEND_COOLDOWN = timedelta(minutes=1)
log = logging.getLogger(__name__)


class RequestPasswordReset:
    def __init__(
        self,
        uow: UnitOfWorkFactory,
        clock: Clock,
        tokens: TokenService,
        mailer: EmailSender,
        link_base: str,
    ) -> None:
        self._uow, self._clock, self._tokens = uow, clock, tokens
        self._mailer, self._link_base = mailer, link_base

    async def __call__(self, email: str) -> None:
        try:
            normalized = normalize_email(email)
        except ValidationError:
            return
        now = self._clock.now()
        async with self._uow() as uow:
            user = await uow.users.get_by_email(normalized)
            if user is None:
                return
            last = await uow.password_resets.latest_created_at(user.id)
            if last is not None and now - last < RESEND_COOLDOWN:
                return  # молча: не подсказываем, что аккаунт существует
            token = self._tokens.new_refresh_token()
            await uow.password_resets.add(
                PasswordResetRecord(
                    self._tokens.hash_refresh_token(token), user.id, now, now + RESET_TTL
                )
            )
            await uow.commit()

        text, html = letter(
            user.full_name,
            "Чтобы задать новый пароль в Студленте УУНиТ, откройте ссылку:",
            f"{self._link_base}?token={token}",
            "Задать новый пароль",
            "Ссылка действует час и сработает один раз. Если вы не просили сменить пароль — "
            "ничего не делайте, старый пароль продолжит работать.",
        )
        try:
            await self._mailer.send(
                EmailMessage(user.email, "Новый пароль — Студлента УУНиТ", text, html)
            )
        except Exception:
            log.exception("Не удалось отправить письмо сброса пароля на %s", user.email)
