"""Console backend - prints emails to stdout. Useful for dev/testing."""

from __future__ import annotations

import logging
import uuid

from .base import EmailBackend, EmailMessage

logger = logging.getLogger(__name__)


class ConsoleBackend:
    """Prints emails to the log instead of sending them."""

    def __init__(self, from_addr: str = "outbot@console.local") -> None:
        self._from_addr = from_addr

    @property
    def from_address(self) -> str:
        return self._from_addr

    async def send(self, message: EmailMessage) -> str:
        msg_id = uuid.uuid4().hex[:12]
        logger.info(
            "--- EMAIL [%s] ---\n"
            "From: %s\nTo: %s\nSubject: %s\n\n%s\n"
            "--- END ---",
            msg_id,
            self._from_addr,
            message.to,
            message.subject,
            message.body,
        )
        return msg_id
