"""Сценарий: отправить письмо со ссылкой подтверждения почты (после регистрации или повторно)."""

import logging
from datetime import timedelta
from html import escape

from studlenta.application.dto import Actor, EmailMessage, EmailVerificationRecord
from studlenta.application.ports import Clock, EmailSender, TokenService, UnitOfWorkFactory
from studlenta.domain.errors import AuthenticationError, ConflictError

TOKEN_TTL = timedelta(hours=24)
RESEND_COOLDOWN = timedelta(minutes=1)
log = logging.getLogger(__name__)


def _letter(name: str, link: str) -> tuple[str, str]:
    text = (
        f"{name}, здравствуйте!\n\n"
        "Подтвердите почту, чтобы предлагать события в ленту Студленты УУНиТ:\n"
        f"{link}\n\n"
        "Ссылка действует сутки. Если вы не регистрировались — просто проигнорируйте письмо.\n"
    )
    html = (
        f"<p>{escape(name)}, здравствуйте!</p>"
        "<p>Подтвердите почту, чтобы предлагать события в ленту Студленты УУНиТ:</p>"
        f'<p><a href="{escape(link)}" style="display:inline-block;padding:12px 20px;'
        "background:#2B59E0;color:#FFFFFF;border-radius:10px;text-decoration:none;"
        'font-weight:600">Подтвердить почту</a></p>'
        f'<p style="color:#4B5563">Или откройте ссылку: {escape(link)}<br>'
        "Ссылка действует сутки. Если вы не регистрировались — просто проигнорируйте письмо.</p>"
    )
    return text, html


class RequestEmailVerification:
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

    async def __call__(self, actor: Actor) -> bool:
        """``True`` — письмо ушло; ``False`` — почта уже подтверждена или SMTP недоступен."""
        now = self._clock.now()
        async with self._uow() as uow:
            user = await uow.users.get(actor.user_id)
            if user is None:
                raise AuthenticationError("Пользователь не найден")
            if user.is_verified:
                return False
            last = await uow.email_verifications.latest_created_at(user.id)
            if last is not None and now - last < RESEND_COOLDOWN:
                raise ConflictError("Письмо уже отправлено — повторить можно через минуту")
            token = self._tokens.new_refresh_token()
            await uow.email_verifications.add(
                EmailVerificationRecord(
                    self._tokens.hash_refresh_token(token), user.id, now, now + TOKEN_TTL
                )
            )
            await uow.commit()

        text, html = _letter(user.full_name, f"{self._link_base}?token={token}")
        try:
            await self._mailer.send(
                EmailMessage(user.email, "Подтвердите почту — Студлента УУНиТ", text, html)
            )
        except Exception:  # почта не должна ломать регистрацию: пользователь запросит письмо снова
            log.exception("Не удалось отправить письмо подтверждения на %s", user.email)
            return False
        return True
