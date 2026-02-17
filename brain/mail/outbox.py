"""Outbox - the public API for sending emails from OutBot.

Usage:
    from brain.mail.outbox import Outbox
    from brain.core.config import Config

    config = Config.load()
    outbox = Outbox.from_config(config)
    await outbox.send(to="troy@example.com", subject="G'day", body="Test email")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from brain.core.events import EmailSent, EventBus

from .backends.base import EmailBackend, EmailMessage
from .backends.console import ConsoleBackend
from .backends.gmail import GmailBackend

logger = logging.getLogger(__name__)


class Outbox:
    """Sends emails via a pluggable backend. Publishes events on success."""

    def __init__(self, backend: EmailBackend, event_bus: EventBus | None = None) -> None:
        self._backend = backend
        self._event_bus = event_bus

    @classmethod
    def from_config(cls, config, event_bus: EventBus | None = None) -> Outbox:
        """Create an Outbox from OutBot Config. Picks backend based on config."""
        backend_name = getattr(config, "email_backend", "console")

        if backend_name == "gmail":
            backend = GmailBackend(
                address=config.email_address,
                app_password=config.email_app_password,
            )
        else:
            backend = ConsoleBackend(
                from_addr=getattr(config, "email_address", "") or "outbot@console.local"
            )

        return cls(backend=backend, event_bus=event_bus)

    @property
    def from_address(self) -> str:
        return self._backend.from_address

    async def send(
        self,
        to: str,
        subject: str,
        body: str,
        html: str = "",
        reply_to: str = "",
    ) -> str:
        """Send an email. Returns a message ID string."""
        message = EmailMessage(
            to=to,
            subject=subject,
            body=body,
            html=html,
            reply_to=reply_to,
        )

        logger.info("Sending email to %s: %s", to, subject)
        msg_id = await self._backend.send(message)

        if self._event_bus:
            self._event_bus.publish(
                EmailSent(to=to, subject=subject, msg_id=msg_id)
            )

        return msg_id
