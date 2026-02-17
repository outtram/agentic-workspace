"""Tests for SQLite database — messages, sessions, scheduled tasks, state."""

import os
import tempfile
import uuid
from datetime import datetime, timezone

import pytest

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.core.db import Database
from brain.core.models import Message


@pytest.fixture
def db():
    """Fresh in-memory-like temp DB for each test."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    database = Database(tmp.name)
    yield database
    database.close()
    os.unlink(tmp.name)


def _msg(content="hello", sender="troy", is_from_me=False, chat_jid="cli@local", ts=None):
    return Message(
        id=str(uuid.uuid4()),
        chat_jid=chat_jid,
        sender=sender,
        sender_name="Troy" if sender == "troy" else "OutBot",
        content=content,
        timestamp=ts or datetime.now(timezone.utc).isoformat(),
        is_from_me=is_from_me,
    )


class TestMessages:
    def test_store_and_retrieve(self, db):
        msg = _msg("hello outbot")
        db.store_message(msg)

        results = db.get_messages_since("cli@local", "", limit=10)
        assert len(results) == 1
        assert results[0].content == "hello outbot"
        assert results[0].sender_name == "Troy"

    def test_multiple_messages_ordered(self, db):
        db.store_message(_msg("first", ts="2026-02-17T00:00:01Z"))
        db.store_message(_msg("second", ts="2026-02-17T00:00:02Z"))
        db.store_message(_msg("third", ts="2026-02-17T00:00:03Z"))

        results = db.get_messages_since("cli@local", "", limit=10)
        assert len(results) == 3
        assert results[0].content == "first"
        assert results[2].content == "third"

    def test_messages_since_timestamp(self, db):
        db.store_message(_msg("old", ts="2026-02-16T00:00:00Z"))
        db.store_message(_msg("new", ts="2026-02-17T12:00:00Z"))

        results = db.get_messages_since("cli@local", "2026-02-17T00:00:00Z")
        assert len(results) == 1
        assert results[0].content == "new"

    def test_messages_limit(self, db):
        for i in range(10):
            db.store_message(_msg(f"msg-{i}", ts=f"2026-02-17T00:00:{i:02d}Z"))

        results = db.get_messages_since("cli@local", "", limit=3)
        assert len(results) == 3

    def test_messages_isolated_by_chat_jid(self, db):
        db.store_message(_msg("cli msg", chat_jid="cli@local"))
        db.store_message(_msg("wa msg", chat_jid="troy@whatsapp"))

        cli = db.get_messages_since("cli@local", "")
        wa = db.get_messages_since("troy@whatsapp", "")
        assert len(cli) == 1
        assert len(wa) == 1
        assert cli[0].content == "cli msg"

    def test_store_both_directions(self, db):
        db.store_message(_msg("from troy", is_from_me=False))
        db.store_message(_msg("from outbot", sender="outbot", is_from_me=True))

        results = db.get_messages_since("cli@local", "")
        assert len(results) == 2
        assert not results[0].is_from_me
        assert results[1].is_from_me


class TestSessions:
    def test_create_and_get_session(self, db):
        db.set_session("cli@local", "session-1")
        session = db.get_session("cli@local")
        assert session is not None
        assert session.session_id == "session-1"

    def test_session_not_found(self, db):
        assert db.get_session("nonexistent") is None

    def test_session_upsert(self, db):
        db.set_session("cli@local", "session-1")
        db.set_session("cli@local", "session-2")
        session = db.get_session("cli@local")
        assert session.session_id == "session-2"


class TestState:
    def test_set_and_get(self, db):
        db.set_state("last_run", "2026-02-17")
        assert db.get_state("last_run") == "2026-02-17"

    def test_get_missing_key(self, db):
        assert db.get_state("nonexistent") is None

    def test_upsert(self, db):
        db.set_state("key", "old")
        db.set_state("key", "new")
        assert db.get_state("key") == "new"


class TestTaskRunLogs:
    def test_log_task_run(self, db):
        # Just verify it doesn't crash — logs are write-only
        db.log_task_run("heartbeat-1", "no action needed", 150)
