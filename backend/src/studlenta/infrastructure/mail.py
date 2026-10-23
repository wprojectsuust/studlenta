"""Отправка писем: SMTP (прод), файл-«ящик» (e2e) и журнал (локальная разработка без почты)."""

import asyncio
import json
import logging
from email.message import EmailMessage as MimeMessage
from email.utils import formataddr, make_msgid
from pathlib import Path

import aiosmtplib

from studlenta.application.dto import EmailMessage

log = logging.getLogger(__name__)


class SmtpEmailSender:
    """Submission (587 + STARTTLS) с авторизацией. DKIM добавляет сам почтовый сервер."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        from_address: str,
        from_name: str,
        starttls: bool = True,
        timeout: float = 15,
    ) -> None:
        self._host, self._port, self._starttls, self._timeout = host, port, starttls, timeout
        self._username, self._password = username, password
        self._from = formataddr((from_name, from_address))
        self._domain = from_address.rsplit("@", 1)[-1]

    async def send(self, message: EmailMessage) -> None:
        mime = MimeMessage()
        mime["From"] = self._from
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime["Message-ID"] = make_msgid(domain=self._domain)
        mime.set_content(message.text)
        mime.add_alternative(message.html, subtype="html")
        await aiosmtplib.send(
            mime, hostname=self._host, port=self._port, start_tls=self._starttls,
            username=self._username, password=self._password, timeout=self._timeout,
        )  # fmt: skip


class FileOutboxSender:
    """Для e2e: письмо пишется JSON-файлом, тест достаёт из него ссылку."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder

    async def send(self, message: EmailMessage) -> None:
        body = {"to": message.to, "subject": message.subject, "text": message.text}
        await asyncio.to_thread(self._write, json.dumps(body, ensure_ascii=False))

    def _write(self, payload: str) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        count = len(list(self._folder.glob("*.json")))
        (self._folder / f"{count:06d}.json").write_text(payload, encoding="utf-8")


class LogEmailSender:
    """Локальная разработка без SMTP: письмо (со ссылкой) просто попадает в лог."""

    async def send(self, message: EmailMessage) -> None:
        log.warning("SMTP не настроен, письмо для %s:\n%s", message.to, message.text)
