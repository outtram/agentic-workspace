"""Inbox - checks for new emails via IMAP.

Usage:
    from brain.mail.inbox import Inbox
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
import ssl
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

GMAIL_IMAP_HOST = "imap.gmail.com"
GMAIL_IMAP_PORT = 993
IMAP_TIMEOUT_SECS = 30
ASYNC_TIMEOUT_SECS = 60


def _make_ssl_context() -> ssl.SSLContext:
    """Build an SSL context that trusts macOS system + corporate proxy certs.

    Corporate proxies often have CA certs with non-critical Basic Constraints,
    which Python 3.13's strict mode rejects. We disable strict X.509 checks
    while keeping hostname + cert chain verification.
    """
    ctx = ssl.create_default_context()

    # Disable strict X.509 mode — corporate proxy certs fail the
    # "Basic Constraints must be critical" check in Python 3.13+
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT

    # Load the combined CA bundle we build for the Claude CLI
    # (includes macOS system roots + corporate proxy CAs)
    from brain.core.claude_client import _get_ca_certs
    ca_path = _get_ca_certs()
    if ca_path:
        try:
            ctx.load_verify_locations(ca_path)
        except Exception:
            pass

    return ctx


def _imap_connect(ssl_ctx: ssl.SSLContext) -> imaplib.IMAP4_SSL:
    """Create an IMAP connection with socket timeout."""
    conn = imaplib.IMAP4_SSL(
        GMAIL_IMAP_HOST, GMAIL_IMAP_PORT, ssl_context=ssl_ctx, timeout=IMAP_TIMEOUT_SECS
    )
    return conn


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

    async def check(self, folder: str = "INBOX", limit: int = 10, unread_only: bool = True) -> list[InboundEmail]:
        """Check for emails. Returns newest first, up to limit."""
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(
                None, self._imap_fetch, folder, limit, unread_only
            ),
            timeout=ASYNC_TIMEOUT_SECS,
        )

    async def mark_read(self, msg_ids: list[str], folder: str = "INBOX") -> int:
        """Mark emails as read by Message-ID. Returns count marked."""
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(
                None, self._imap_mark_read, msg_ids, folder
            ),
            timeout=ASYNC_TIMEOUT_SECS,
        )

    def _imap_mark_read(self, msg_ids: list[str], folder: str) -> int:
        """Blocking IMAP mark-as-read — called via run_in_executor."""
        ssl_ctx = _make_ssl_context()
        conn = _imap_connect(ssl_ctx)
        marked = 0
        try:
            logger.debug("IMAP mark_read: logging in...")
            conn.login(self._address, self._app_password)
            conn.select(folder, readonly=False)

            for mid in msg_ids:
                safe_id = mid.replace('"', '\\"')
                status, data = conn.search(
                    None, f'HEADER Message-ID "{safe_id}"'
                )
                if status != "OK" or not data[0]:
                    continue
                for seq_num in data[0].split():
                    conn.store(seq_num, "+FLAGS", "\\Seen")
                    marked += 1

            conn.close()
            conn.logout()
            logger.debug("IMAP mark_read: done, marked=%d", marked)
        except Exception as e:
            logger.error("IMAP mark_read failed: %s", e)
            try:
                conn.logout()
            except Exception:
                pass
            raise
        return marked

    def _imap_fetch(self, folder: str, limit: int, unread_only: bool = True) -> list[InboundEmail]:
        """Blocking IMAP fetch with retry — called via run_in_executor.

        Corporate proxies and Gmail can drop IMAP connections intermittently
        (EOF on second connect). We retry once after a brief pause.
        """
        last_error: Exception | None = None

        for attempt in range(2):  # Try twice
            if attempt > 0:
                logger.info("IMAP retry (attempt %d)...", attempt + 1)
                time.sleep(1.5)  # Brief pause before retry

            try:
                return self._imap_fetch_once(folder, limit, unread_only)
            except (OSError, imaplib.IMAP4.error, TimeoutError) as e:
                last_error = e
                err_str = str(e)
                if any(k in err_str for k in ("EOF", "reset", "timed out", "Broken pipe", "Timeout")):
                    logger.warning("IMAP connection failed (attempt %d): %s", attempt + 1, e)
                    continue
                raise RuntimeError(f"Gmail IMAP error: {e}") from e
            except Exception as e:
                logger.error("Inbox check failed: %s", e)
                raise

        raise RuntimeError(f"Gmail IMAP failed after 2 attempts: {last_error}") from last_error

    def _imap_fetch_once(self, folder: str, limit: int, unread_only: bool) -> list[InboundEmail]:
        """Single IMAP fetch attempt."""
        results: list[InboundEmail] = []

        ssl_ctx = _make_ssl_context()
        logger.debug("IMAP connect: %s:%d (timeout=%ds)", GMAIL_IMAP_HOST, GMAIL_IMAP_PORT, IMAP_TIMEOUT_SECS)
        conn = _imap_connect(ssl_ctx)
        try:
            logger.debug("IMAP login: %s", self._address)
            conn.login(self._address, self._app_password)
            logger.debug("IMAP select: %s", folder)
            conn.select(folder, readonly=True)

            criteria = "UNSEEN" if unread_only else "ALL"
            logger.debug("IMAP search: %s", criteria)
            status, data = conn.search(None, criteria)
            if status != "OK" or not data[0]:
                logger.debug("IMAP search: no results")
                conn.close()
                conn.logout()
                return results

            msg_ids = data[0].split()
            recent_ids = msg_ids[-limit:]
            logger.debug("IMAP found %d messages, fetching %d", len(msg_ids), len(recent_ids))

            for i, mid in enumerate(reversed(recent_ids)):  # Newest first
                logger.debug("IMAP fetch %d/%d: seq=%s", i + 1, len(recent_ids), mid.decode())
                status, msg_data = conn.fetch(mid, "(RFC822)")
                if status != "OK":
                    logger.warning("IMAP fetch failed for seq=%s", mid.decode())
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

                subj = msg.get("Subject", "(no subject)")
                logger.debug("IMAP parsed: %s — %s", sender_addr, subj[:60])

                results.append(InboundEmail(
                    msg_id=msg.get("Message-ID", mid.decode()),
                    sender=sender_addr,
                    sender_name=sender_name or sender_addr,
                    subject=subj,
                    body=body.strip()[:2000],
                    date=msg.get("Date", ""),
                    to=msg.get("To", ""),
                ))

            conn.close()
            conn.logout()
            logger.debug("IMAP done: %d emails fetched", len(results))
            self._last_check = datetime.now(timezone.utc)
        except Exception as e:
            logger.error("IMAP fetch_once failed: %s", e)
            try:
                conn.logout()
            except Exception:
                pass
            raise

        return results
