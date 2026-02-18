"""Tests for the email inbox module."""

from __future__ import annotations

import email
import imaplib
from email.message import EmailMessage as StdEmailMessage
from unittest.mock import MagicMock, patch, call

import pytest

from brain.mail.inbox import Inbox, InboundEmail, GMAIL_IMAP_HOST


class TestInboundEmail:
    def test_fields(self):
        e = InboundEmail(
            msg_id="abc",
            sender="troy@test.com",
            sender_name="Troy",
            subject="G'day",
            body="Hello mate",
            date="Mon, 17 Feb 2026 10:00:00 +0000",
        )
        assert e.sender == "troy@test.com"
        assert e.sender_name == "Troy"
        assert e.to == ""  # Default


class TestInboxValidation:
    def test_requires_address(self):
        with pytest.raises(ValueError, match="OUTBOT_EMAIL_ADDRESS"):
            Inbox(address="", app_password="secret")

    def test_requires_app_password(self):
        with pytest.raises(ValueError, match="OUTBOT_EMAIL_APP_PASSWORD"):
            Inbox(address="bot@gmail.com", app_password="")


class TestInboxFromConfig:
    def test_from_config(self):
        config = MagicMock()
        config.email_address = "bot@gmail.com"
        config.email_app_password = "secret"
        inbox = Inbox.from_config(config)
        assert inbox._address == "bot@gmail.com"


class TestImapFetch:
    def _make_raw_email(self, sender="troy@test.com", subject="Test", body="Hello"):
        """Build a raw RFC822 email bytes object for mocking."""
        msg = StdEmailMessage()
        msg["From"] = f"Troy <{sender}>"
        msg["To"] = "bot@gmail.com"
        msg["Subject"] = subject
        msg["Message-ID"] = "<test-123@mail.gmail.com>"
        msg["Date"] = "Mon, 17 Feb 2026 10:00:00 +0000"
        msg.set_content(body)
        return msg.as_bytes()

    @patch("brain.mail.inbox.imaplib.IMAP4_SSL")
    def test_fetch_unread(self, mock_imap_cls):
        """Should parse unread emails from IMAP."""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn

        # Simulate IMAP responses
        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"3"])
        mock_conn.search.return_value = ("OK", [b"1 2 3"])
        raw = self._make_raw_email(subject="G'day mate", body="How's it going?")
        mock_conn.fetch.return_value = ("OK", [(b"1 (RFC822 {1234}", raw)])

        inbox = Inbox(address="bot@gmail.com", app_password="secret")
        results = inbox._imap_fetch("INBOX", limit=5)

        assert len(results) == 3  # 3 message IDs
        assert results[0].subject == "G'day mate"
        assert results[0].sender == "troy@test.com"
        assert results[0].sender_name == "Troy"
        assert "How's it going?" in results[0].body

    @patch("brain.mail.inbox.imaplib.IMAP4_SSL")
    def test_fetch_empty_inbox(self, mock_imap_cls):
        """Should return empty list when no unread emails."""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn

        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"0"])
        mock_conn.search.return_value = ("OK", [b""])

        inbox = Inbox(address="bot@gmail.com", app_password="secret")
        results = inbox._imap_fetch("INBOX", limit=5)

        assert results == []

    @patch("brain.mail.inbox.imaplib.IMAP4_SSL")
    def test_fetch_respects_limit(self, mock_imap_cls):
        """Should only return up to `limit` most recent emails."""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn

        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"10"])
        mock_conn.search.return_value = ("OK", [b"1 2 3 4 5 6 7 8 9 10"])
        raw = self._make_raw_email()
        mock_conn.fetch.return_value = ("OK", [(b"1 (RFC822 {1234}", raw)])

        inbox = Inbox(address="bot@gmail.com", app_password="secret")
        results = inbox._imap_fetch("INBOX", limit=3)

        # Should only fetch 3 messages (IDs 8, 9, 10)
        assert mock_conn.fetch.call_count == 3

    @patch("brain.mail.inbox.imaplib.IMAP4_SSL")
    def test_body_truncated_at_2000_chars(self, mock_imap_cls):
        """Long email bodies should be capped."""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn

        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"1"])
        mock_conn.search.return_value = ("OK", [b"1"])
        raw = self._make_raw_email(body="x" * 5000)
        mock_conn.fetch.return_value = ("OK", [(b"1 (RFC822 {1234}", raw)])

        inbox = Inbox(address="bot@gmail.com", app_password="secret")
        results = inbox._imap_fetch("INBOX", limit=5)

        assert len(results[0].body) <= 2000

    @pytest.mark.asyncio
    @patch("brain.mail.inbox.imaplib.IMAP4_SSL")
    async def test_check_async(self, mock_imap_cls):
        """The async check() method should work."""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn

        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"0"])
        mock_conn.search.return_value = ("OK", [b""])

        inbox = Inbox(address="bot@gmail.com", app_password="secret")
        results = await inbox.check()

        assert results == []

    @patch("brain.mail.inbox.imaplib.IMAP4_SSL")
    def test_fetch_all_not_just_unread(self, mock_imap_cls):
        """unread_only=False should search ALL, not UNSEEN."""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn

        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"5"])
        mock_conn.search.return_value = ("OK", [b""])

        inbox = Inbox(address="bot@gmail.com", app_password="secret")
        inbox._imap_fetch_once("INBOX", limit=5, unread_only=False)

        mock_conn.search.assert_called_once_with(None, "ALL")

    @patch("brain.mail.inbox.imaplib.IMAP4_SSL")
    def test_fetch_unread_uses_unseen(self, mock_imap_cls):
        """unread_only=True should search UNSEEN."""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn

        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"5"])
        mock_conn.search.return_value = ("OK", [b""])

        inbox = Inbox(address="bot@gmail.com", app_password="secret")
        inbox._imap_fetch_once("INBOX", limit=5, unread_only=True)

        mock_conn.search.assert_called_once_with(None, "UNSEEN")


class TestImapRetry:
    """Tests for IMAP retry logic on transient connection errors."""

    @patch("brain.mail.inbox.time.sleep")
    @patch("brain.mail.inbox.imaplib.IMAP4_SSL")
    def test_retries_on_eof(self, mock_imap_cls, mock_sleep):
        """Should retry once when connection gets EOF."""
        # First call: EOF error. Second call: success.
        mock_conn_fail = MagicMock()
        mock_conn_fail.login.side_effect = OSError("socket error: EOF")

        mock_conn_ok = MagicMock()
        mock_conn_ok.login.return_value = ("OK", [])
        mock_conn_ok.select.return_value = ("OK", [b"0"])
        mock_conn_ok.search.return_value = ("OK", [b""])

        mock_imap_cls.side_effect = [mock_conn_fail, mock_conn_ok]

        inbox = Inbox(address="bot@gmail.com", app_password="secret")
        results = inbox._imap_fetch("INBOX", limit=5)

        assert results == []
        assert mock_imap_cls.call_count == 2
        mock_sleep.assert_called_once_with(1.5)

    @patch("brain.mail.inbox.time.sleep")
    @patch("brain.mail.inbox.imaplib.IMAP4_SSL")
    def test_no_retry_on_auth_failure(self, mock_imap_cls, mock_sleep):
        """Should NOT retry on authentication failures."""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn
        mock_conn.login.side_effect = imaplib.IMAP4.error("AUTHENTICATIONFAILED")

        inbox = Inbox(address="bot@gmail.com", app_password="secret")
        with pytest.raises(RuntimeError, match="Gmail IMAP error"):
            inbox._imap_fetch("INBOX", limit=5)

        # Should NOT have retried
        assert mock_imap_cls.call_count == 1
        mock_sleep.assert_not_called()

    @patch("brain.mail.inbox.time.sleep")
    @patch("brain.mail.inbox.imaplib.IMAP4_SSL")
    def test_fails_after_two_eof_attempts(self, mock_imap_cls, mock_sleep):
        """Should raise after both attempts fail with EOF."""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn
        mock_conn.login.side_effect = OSError("socket error: EOF")

        inbox = Inbox(address="bot@gmail.com", app_password="secret")
        with pytest.raises(RuntimeError, match="failed after 2 attempts"):
            inbox._imap_fetch("INBOX", limit=5)

        assert mock_imap_cls.call_count == 2

    @patch("brain.mail.inbox.imaplib.IMAP4_SSL")
    def test_success_on_first_try_no_retry(self, mock_imap_cls):
        """Should not retry when first attempt succeeds."""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn

        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"0"])
        mock_conn.search.return_value = ("OK", [b""])

        inbox = Inbox(address="bot@gmail.com", app_password="secret")
        results = inbox._imap_fetch("INBOX", limit=5)

        assert results == []
        assert mock_imap_cls.call_count == 1  # Only one attempt

    @patch("brain.mail.inbox.time.sleep")
    @patch("brain.mail.inbox.imaplib.IMAP4_SSL")
    def test_cleans_up_on_error(self, mock_imap_cls, mock_sleep):
        """Should attempt logout on error to clean up connection."""
        mock_conn = MagicMock()
        mock_imap_cls.return_value = mock_conn
        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"5"])
        mock_conn.search.side_effect = OSError("socket error: EOF")

        inbox = Inbox(address="bot@gmail.com", app_password="secret")
        with pytest.raises(RuntimeError, match="failed after 2 attempts"):
            inbox._imap_fetch("INBOX", limit=5)

        # Should have tried to logout on each failed attempt
        assert mock_conn.logout.call_count >= 1
