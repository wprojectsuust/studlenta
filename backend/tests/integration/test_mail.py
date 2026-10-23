"""Отправка писем по настоящему SMTP-протоколу на локальный тестовый сервер (aiosmtpd)."""

import asyncio
import email
import socket
from collections.abc import AsyncIterator
from email import policy
from pathlib import Path

import aiosmtplib
import pytest
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Message
from aiosmtpd.smtp import AuthResult, LoginPassword

from studlenta.application.dto import EmailMessage
from studlenta.infrastructure.mail import FileOutboxSender, SmtpEmailSender

pytestmark = pytest.mark.integration


class Collect(Message):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[email.message.EmailMessage] = []

    def handle_message(self, message: email.message.Message) -> None:
        raw = message.as_bytes()
        self.messages.append(email.message_from_bytes(raw, policy=policy.default))  # type: ignore[arg-type]


def authenticator(server, session, envelope, mechanism, auth_data):  # type: ignore[no-untyped-def]
    ok = isinstance(auth_data, LoginPassword) and auth_data.password == b"secret"
    return AuthResult(success=ok)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
async def smtp() -> AsyncIterator[tuple[Collect, int]]:
    handler = Collect()
    port = free_port()
    controller = Controller(
        handler,
        hostname="127.0.0.1",
        port=port,
        authenticator=authenticator,
        auth_require_tls=False,
    )
    controller.start()
    yield handler, port
    controller.stop()


LETTER = EmailMessage(
    "anna@uust.ru",
    "Подтвердите почту — Студлента УУНиТ",
    "Ссылка: https://x/verify?token=t",
    '<a href="https://x/verify?token=t">ok</a>',
)


async def test_smtp_sender_authenticates_and_sends_multipart(smtp: tuple[Collect, int]) -> None:
    handler, port = smtp
    sender = SmtpEmailSender(
        host="127.0.0.1",
        port=port,
        username="studlenta@karrad.tech",
        password="secret",
        from_address="studlenta@karrad.tech",
        from_name="Студлента УУНиТ",
        starttls=False,
    )
    await sender.send(LETTER)
    for _ in range(50):
        if handler.messages:
            break
        await asyncio.sleep(0.02)
    [msg] = handler.messages
    assert msg["To"] == "anna@uust.ru"
    assert "studlenta@karrad.tech" in msg["From"]
    assert msg["Subject"] == "Подтвердите почту — Студлента УУНиТ"
    assert msg["Message-ID"].endswith("@karrad.tech>")
    assert msg.get_body(("plain",)).get_content().strip() == "Ссылка: https://x/verify?token=t"
    assert "token=t" in msg.get_body(("html",)).get_content()


async def test_unreachable_server_is_an_error() -> None:
    sender = SmtpEmailSender(
        host="127.0.0.1",
        port=free_port(),
        username="u",
        password="p",
        from_address="studlenta@karrad.tech",
        from_name="Студлента",
        starttls=False,
        timeout=2,
    )
    with pytest.raises(aiosmtplib.SMTPException):
        await sender.send(LETTER)


async def test_file_outbox_for_e2e(tmp_path: Path) -> None:
    sender = FileOutboxSender(tmp_path)
    await sender.send(LETTER)
    [file] = list(tmp_path.glob("*.json"))
    assert "token=t" in file.read_text(encoding="utf-8")
