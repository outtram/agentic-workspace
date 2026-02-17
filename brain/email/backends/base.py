"""Abstract base for email backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class EmailMessage:
    """A single outbound email."""

    to: str
    subject: str
    body: str
    html: str = ""
    reply_to: str = ""


@runtime_checkable
class EmailBackend(Protocol):
    """Interface that all email backends must implement."""

    async def send(self, message: EmailMessage) -> str:
        """Send an email, return a message ID or receipt string."""
        ...

    @property
    def from_address(self) -> str:
        """The sender address this backend sends from."""
        ...
