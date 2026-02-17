"""Inbox - checks for new emails via IMAP.

Usage:
    from brain.email.inbox import Inbox
    from brain.core.config import Config

    config = Config.load()
    inbox = Inbox.from_config(config)
    emails = await inbox.check()
"""

from __future__ import annotations

import asyncio
import email
import email.utils
import imaplib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

GMAIL_IMAP_HOST = "imap.gmail.com"
GMAIL_IMAP_PORT = 993


@dataclass
class InboundEmail:
    """A received email."""

    msg_id: str
    sender: str
    sender_name: str
    subject: str
    body: str
    date: str
    to: str = ""


class Inbox:
    """Checks for new emails via Gmail IMAP."""

    def __init__(self, address: str, app_password: str) -> None:
        if not address:
            raise ValueError("OUTBOT_EMAIL_ADDRESS is required for Inbox")
        if not app_password:
            raise ValueError("OUTBOT_EMAIL_APP_PASSWORD is required for Inbox")
        self._address = address
        self._app_password = app_password
        self._last_check: datetime | None = None

    @classmethod
    def from_config(cls, config) -> Inbox:
        """Create an Inbox from OutBot Config."""
        return cls(
            address=config.email_address,
            app_password=config.email_app_password,
        )

    async def check(self, folder: str = "INBOX", limit: int = 5) -> list[InboundEmail]:
        """Check for unread emails. Returns newest first, up to limit."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._imap_fetch, folder, limit
        )

    def _imap_fetch(self, folder: str, limit: int) -> list[InboundEmail]:
        """Blocking IMAP fetch — called via run_in_executor."""
        results: list[InboundEmail] = []

        try:
            conn = imaplib.IMAP4_SSL(GMAIL_IMAP_HOST, GMAIL_IMAP_PORT)
            conn.login(self._address, self._app_password)
            conn.select(folder, readonly=True)

            # Search for unseen messages
            status, data = conn.search(None, "UNSEEN")
            if status != "OK" or not data[0]:
                conn.close()
                conn.logout()
                return results

            msg_ids = data[0].split()
            # Take the most recent N
            recent_ids = msg_ids[-limit:]

            for mid in reversed(recent_ids):  # Newest first
                status, msg_data = conn.fetch(mid, "(RFC822)")
                if status != "OK":
                    continue

                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                # Extract body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body = payload.decode("utf-8", errors="replace")
                            break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="replace")

                # Parse sender
                from_header = msg.get("From", "")
                sender_name, sender_addr = email.utils.parseaddr(from_header)

                results.append(InboundEmail(
                    msg_id=msg.get("Message-ID", mid.decode()),
                    sender=sender_addr,
                    sender_name=sender_name or sender_addr,
                    subject=msg.get("Subject", "(no subject)"),
                    body=body.strip()[:2000],  # Cap body length
                    date=msg.get("Date", ""),
                    to=msg.get("To", ""),
                ))

            conn.close()
            conn.logout()
            self._last_check = datetime.now(timezone.utc)

        except imaplib.IMAP4.error as e:
            logger.error("IMAP error: %s", e)
            raise RuntimeError(f"Gmail IMAP error: {e}") from e
        except Exception as e:
            logger.error("Inbox check failed: %s", e)
            raise

        return results
