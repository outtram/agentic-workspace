"""Tests for session manager and catch-up context formatting."""

import os
import tempfile

import pytest

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.core.db import Database
from brain.core.events import EventBus
from brain.core.models import Message
from brain.session.context import escape_xml, format_catchup, format_catchup_summary
from brain.session.manager import SessionManager


@pytest.fixture
def db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    database = Database(tmp.name)
    yield database
    database.close()
    os.unlink(tmp.name)


def _msg(content, sender="Troy", ts="2026-02-17T12:00:00Z"):
    return Message(
        id="id-1", chat_jid="cli@local", sender="troy",
        sender_name=sender, content=content, timestamp=ts, is_from_me=False,
    )


class TestSessionManager:
    def test_creates_new_session(self, db):
        mgr = SessionManager(db, EventBus())
        session = mgr.get_or_create_session("cli@local")
        assert session.chat_jid == "cli@local"
        assert session.session_id  # Not empty

    def test_returns_existing_session(self, db):
        mgr = SessionManager(db, EventBus())
        s1 = mgr.get_or_create_session("cli@local")
        s2 = mgr.get_or_create_session("cli@local")
        assert s1.session_id == s2.session_id

    def test_publishes_session_started_event(self, db):
        events = []
        bus = EventBus()
        from brain.core.events import SessionStarted
        bus.subscribe(SessionStarted, lambda e: events.append(e))

        mgr = SessionManager(db, bus)
        mgr.get_or_create_session("cli@local")
        assert len(events) == 1
        assert events[0].chat_jid == "cli@local"

    def test_different_chats_get_different_sessions(self, db):
        mgr = SessionManager(db, EventBus())
        s1 = mgr.get_or_create_session("chat-a")
        s2 = mgr.get_or_create_session("chat-b")
        assert s1.session_id != s2.session_id


class TestEscapeXml:
    def test_escapes_ampersand(self):
        assert escape_xml("A & B") == "A &amp; B"

    def test_escapes_angle_brackets(self):
        assert escape_xml("<tag>") == "&lt;tag&gt;"

    def test_escapes_quotes(self):
        assert escape_xml('say "hi"') == "say &quot;hi&quot;"


class TestFormatCatchup:
    def test_empty_list(self):
        assert format_catchup([]) == ""

    def test_single_message(self):
        result = format_catchup([_msg("hello")])
        assert "<messages>" in result
        assert 'sender="Troy"' in result
        assert "hello" in result
        assert "</messages>" in result

    def test_multiple_messages(self):
        msgs = [_msg("first"), _msg("second", sender="OutBot")]
        result = format_catchup(msgs)
        assert result.count("<message ") == 2

    def test_escapes_content(self):
        result = format_catchup([_msg("A & B <tag>")])
        assert "&amp;" in result
        assert "&lt;" in result


class TestFormatCatchupSummary:
    def test_small_list_unchanged(self):
        msgs = [_msg(f"msg-{i}") for i in range(5)]
        result = format_catchup_summary(msgs)
        assert result.count("<message ") == 5

    def test_large_list_truncated(self):
        msgs = [_msg(f"msg-{i}", ts=f"2026-02-17T{i:02d}:00:00Z") for i in range(60)]
        result = format_catchup_summary(msgs, max_messages=50)
        assert "<gap" in result
        # Should have head + tail messages, not all 60
        assert result.count("<message") < 60
