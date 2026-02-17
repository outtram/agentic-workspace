"""Gmail SMTP backend - sends via smtp.gmail.com with an App Password.

Setup:
  1. Create a Gmail account (e.g. outbot.agentic@gmail.com)
  2. Enable 2-Step Verification on that account
  3. Generate an App Password: Google Account > Security > App Passwords
  4. Set OUTBOT_EMAIL_ADDRESS and OUTBOT_EMAIL_APP_PASSWORD in .env
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage as StdEmailMessage

from .base import EmailBackend, EmailMessage

logger = logging.getLogger(__name__)

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


class GmailBackend:
    """Sends email via Gmail SMTP with App Password auth."""

    def __init__(self, address: str, app_password: str) -> None:
        if not address:
            raise ValueError("OUTBOT_EMAIL_ADDRESS is required for Gmail backend")
        if not app_password:
            raise ValueError("OUTBOT_EMAIL_APP_PASSWORD is required for Gmail backend")
        self._address = address
        self._app_password = app_password

    @property
    def from_address(self) -> str:
        return self._address

    async def send(self, message: EmailMessage) -> str:
        """Send email via Gmail SMTP. Runs blocking SMTP in a thread."""
        msg = self._build_message(message)
        # Run blocking SMTP call in executor to keep async loop free
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self._smtp_send, msg)
        return result

    def _build_message(self, message: EmailMessage) -> StdEmailMessage:
        msg = StdEmailMessage()
        msg["From"] = self._address
        msg["To"] = message.to
        msg["Subject"] = message.subject

        if message.reply_to:
            msg["Reply-To"] = message.reply_to

        if message.html:
            msg.set_content(message.body)
            msg.add_alternative(message.html, subtype="html")
        else:
            msg.set_content(message.body)

        return msg

    def _smtp_send(self, msg: StdEmailMessage) -> str:
        """Blocking SMTP send - called via run_in_executor."""
        try:
            with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
                server.starttls()
                server.login(self._address, self._app_password)
                server.send_message(msg)
                msg_id = msg["Message-ID"] or "sent"
                logger.info("Email sent to %s: %s", msg["To"], msg["Subject"])
                return str(msg_id)
        except smtplib.SMTPAuthenticationError:
            logger.error(
                "Gmail auth failed. Check OUTBOT_EMAIL_APP_PASSWORD. "
                "Make sure 2-Step Verification is on and you're using an App Password."
            )
            raise
