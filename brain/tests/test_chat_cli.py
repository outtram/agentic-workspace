"""Tests for the OutBot CLI — full pipeline integration tests."""

import asyncio
import os
import tempfile
import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.chat import OutBotCLI
from brain.core.config import Config
from brain.core.db import Database


@pytest.fixture
def cli(monkeypatch):
    """OutBotCLI with a temp database."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setenv("OUTBOT_DB_PATH", tmp.name)
    instance = OutBotCLI(voice=False)
    yield instance
    instance.db.close()
    os.unlink(tmp.name)


class TestOutBotCLI:
    def test_init_loads_components(self, cli):
        assert cli.db is not None
        assert cli.sessions is not None
        assert cli.personality_loader is not None
        assert cli.claude is not None

    def test_store_message(self, cli):
        msg = cli._store_message("test", sender="troy", is_from_me=False)
        assert msg.content == "test"
        assert msg.sender_name == "Troy"

        # Verify it's in the DB
        results = cli.db.get_messages_since("cli@local", "")
        assert len(results) == 1

    def test_store_outbot_reply(self, cli):
        msg = cli._store_message("reply", sender="outbot", is_from_me=True)
        assert msg.sender_name == "OutBot"
        assert msg.is_from_me is True

    def test_get_context_empty(self, cli):
        context = cli._get_context()
        # With no messages, context should be empty
        assert context == "" or "<messages>" in context

    def test_get_context_with_messages(self, cli):
        cli._store_message("hello", sender="troy", is_from_me=False)
        cli._store_message("hi there", sender="outbot", is_from_me=True)
        context = cli._get_context()
        assert "<messages>" in context
        assert "hello" in context
        assert "hi there" in context

    def test_conversation_builds_context(self, cli):
        """Each message should add to the context window."""
        cli._store_message("first", sender="troy", is_from_me=False)
        cli._store_message("reply 1", sender="outbot", is_from_me=True)
        cli._store_message("second", sender="troy", is_from_me=False)

        context = cli._get_context()
        assert "first" in context
        assert "reply 1" in context
        assert "second" in context


class TestEmailDetection:
    """Tests for email intent detection — must handle natural phrasing."""

    def test_check_email(self, cli):
        assert cli._is_email_check("check my email")

    def test_check_emails(self, cli):
        assert cli._is_email_check("check my emails")

    def test_any_new_emails(self, cli):
        assert cli._is_email_check("any new emails?")

    def test_show_inbox(self, cli):
        assert cli._is_email_check("show me my inbox")

    def test_inbox_alone(self, cli):
        assert cli._is_email_check("inbox")

    def test_latest_emails(self, cli):
        assert cli._is_email_check("check my latest emails")

    def test_look_at_emails(self, cli):
        assert cli._is_email_check("look at my emails")

    def test_read_email(self, cli):
        assert cli._is_email_check("read my email")

    def test_view_emails(self, cli):
        assert cli._is_email_check("view emails")

    def test_open_mail(self, cli):
        assert cli._is_email_check("open my mail")

    def test_look_at_external_emails(self, cli):
        assert cli._is_email_check("look at external emails about a failure")

    def test_not_email_check_generic(self, cli):
        """Generic messages should NOT trigger email check."""
        assert not cli._is_email_check("hello mate")
        assert not cli._is_email_check("what's on today?")
        assert not cli._is_email_check("remember I like coffee")

    def test_not_email_check_question_about_email(self, cli):
        """Questions about email capability shouldn't trigger a check."""
        assert not cli._is_email_check("can you do email?")

    def test_send_email(self, cli):
        assert cli._is_email_send("send an email to troy")

    def test_send_me_test_email(self, cli):
        assert cli._is_email_send("can you send me a test email")

    def test_compose_email(self, cli):
        assert cli._is_email_send("compose an email")

    def test_draft_email(self, cli):
        assert cli._is_email_send("draft an email to the team")

    def test_not_send_generic(self, cli):
        assert not cli._is_email_send("send me a joke")
        assert not cli._is_email_send("what should I send?")

    def test_unread_only_flag(self, cli):
        """'unread' or 'new' in text should set unread_only."""
        words_new = cli._words("any new emails?")
        assert bool(words_new & {"unread", "new", "unseen"})

        words_all = cli._words("check my emails")
        assert not bool(words_all & {"unread", "new", "unseen"})

        words_unread = cli._words("show unread emails")
        assert bool(words_unread & {"unread", "new", "unseen"})


class TestOutBotCLILive:
    """Live integration tests — actually calls Claude."""

    @pytest.mark.slow
    def test_send_and_receive(self, cli):
        reply = asyncio.run(cli.send("Say exactly: HELLO TROY"))
        assert "HELLO" in reply.upper() or "TROY" in reply.upper()

    @pytest.mark.slow
    def test_conversation_memory(self, cli):
        """OutBot should remember what was said earlier in the session."""
        asyncio.run(cli.send("My favourite colour is purple. Just acknowledge."))
        reply = asyncio.run(cli.send("What did I just say my favourite colour is?"))
        assert "purple" in reply.lower()
