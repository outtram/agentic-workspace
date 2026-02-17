"""Tests for the email outbox module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from brain.core.config import Config
from brain.core.events import EmailSent, EventBus
from brain.mail.backends.base import EmailMessage
from brain.mail.backends.console import ConsoleBackend
from brain.mail.backends.gmail import GmailBackend
from brain.mail.outbox import Outbox


class TestEmailMessage:
    def test_defaults(self):
        msg = EmailMessage(to="a@b.com", subject="Hi", body="Hello")
        assert msg.html == ""
        assert msg.reply_to == ""

    def test_all_fields(self):
        msg = EmailMessage(
            to="a@b.com",
            subject="Hi",
            body="Hello",
            html="<p>Hello</p>",
            reply_to="reply@b.com",
        )
        assert msg.html == "<p>Hello</p>"
        assert msg.reply_to == "reply@b.com"


class TestConsoleBackend:
    @pytest.mark.asyncio
    async def test_send_returns_msg_id(self):
        backend = ConsoleBackend()
        msg = EmailMessage(to="troy@test.com", subject="Test", body="G'day")
        result = await backend.send(msg)
        assert isinstance(result, str)
        assert len(result) == 12  # hex UUID slice

    def test_from_address_default(self):
        backend = ConsoleBackend()
        assert backend.from_address == "outbot@console.local"

    def test_from_address_custom(self):
        backend = ConsoleBackend(from_addr="custom@test.com")
        assert backend.from_address == "custom@test.com"


class TestGmailBackend:
    def test_requires_address(self):
        with pytest.raises(ValueError, match="OUTBOT_EMAIL_ADDRESS"):
            GmailBackend(address="", app_password="secret")

    def test_requires_app_password(self):
        with pytest.raises(ValueError, match="OUTBOT_EMAIL_APP_PASSWORD"):
            GmailBackend(address="bot@gmail.com", app_password="")

    def test_from_address(self):
        backend = GmailBackend(address="bot@gmail.com", app_password="secret")
        assert backend.from_address == "bot@gmail.com"

    def test_build_message_plain(self):
        backend = GmailBackend(address="bot@gmail.com", app_password="secret")
        msg = EmailMessage(to="troy@test.com", subject="G'day", body="Hello mate")
        result = backend._build_message(msg)
        assert result["To"] == "troy@test.com"
        assert result["Subject"] == "G'day"
        assert result["From"] == "bot@gmail.com"

    def test_build_message_with_html(self):
        backend = GmailBackend(address="bot@gmail.com", app_password="secret")
        msg = EmailMessage(
            to="troy@test.com",
            subject="Hi",
            body="Plain text",
            html="<p>HTML</p>",
        )
        result = backend._build_message(msg)
        # Should have multipart content
        assert result.is_multipart()

    def test_build_message_with_reply_to(self):
        backend = GmailBackend(address="bot@gmail.com", app_password="secret")
        msg = EmailMessage(
            to="troy@test.com",
            subject="Hi",
            body="text",
            reply_to="other@test.com",
        )
        result = backend._build_message(msg)
        assert result["Reply-To"] == "other@test.com"


class TestOutbox:
    @pytest.mark.asyncio
    async def test_send_with_console_backend(self):
        outbox = Outbox(backend=ConsoleBackend())
        msg_id = await outbox.send(
            to="troy@test.com", subject="Test", body="G'day mate"
        )
        assert isinstance(msg_id, str)

    @pytest.mark.asyncio
    async def test_send_publishes_event(self):
        event_bus = EventBus()
        received = []
        event_bus.subscribe(EmailSent, lambda e: received.append(e))

        outbox = Outbox(backend=ConsoleBackend(), event_bus=event_bus)
        await outbox.send(to="troy@test.com", subject="Test", body="Hello")

        assert len(received) == 1
        assert received[0].to == "troy@test.com"
        assert received[0].subject == "Test"

    @pytest.mark.asyncio
    async def test_send_no_event_bus(self):
        """Should work fine without an event bus."""
        outbox = Outbox(backend=ConsoleBackend(), event_bus=None)
        msg_id = await outbox.send(to="troy@test.com", subject="Test", body="Hello")
        assert msg_id  # No crash, returns ID

    def test_from_config_console(self):
        config = MagicMock(spec=Config)
        config.email_backend = "console"
        config.email_address = ""
        outbox = Outbox.from_config(config)
        assert outbox.from_address == "outbot@console.local"

    def test_from_config_gmail(self):
        config = MagicMock(spec=Config)
        config.email_backend = "gmail"
        config.email_address = "bot@gmail.com"
        config.email_app_password = "secret"
        outbox = Outbox.from_config(config)
        assert outbox.from_address == "bot@gmail.com"

    def test_from_config_defaults_to_console(self):
        config = MagicMock(spec=Config)
        config.email_backend = "unknown"
        config.email_address = ""
        outbox = Outbox.from_config(config)
        assert outbox.from_address == "outbot@console.local"
