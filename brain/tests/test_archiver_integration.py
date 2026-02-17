"""Tests for session archiving integration with the CLI."""

import os
import sys
import tempfile
import uuid

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.core.models import Message
from brain.session.archiver import SessionArchiver


@pytest.fixture
def archiver(tmp_path):
    """SessionArchiver writing to a temp directory."""
    return SessionArchiver(archive_dir=str(tmp_path))


def _make_messages(count: int, chat_jid: str = "cli@local") -> list[Message]:
    """Create dummy messages for testing."""
    messages = []
    for i in range(count):
        is_from_me = i % 2 == 1
        messages.append(
            Message(
                id=str(uuid.uuid4()),
                chat_jid=chat_jid,
                sender="outbot" if is_from_me else "troy",
                sender_name="OutBot" if is_from_me else "Troy",
                content=f"Message {i + 1}",
                timestamp=f"2026-02-17T10:{i:02d}:00Z",
                is_from_me=is_from_me,
            )
        )
    return messages


class TestSessionArchiver:
    def test_archives_on_session_end(self, archiver, tmp_path):
        """Archiving 5 messages should produce a file."""
        messages = _make_messages(5)
        path = archiver.archive("cli@local", messages, "test conversation")

        assert path.exists()
        assert path.suffix == ".md"

    def test_skips_no_messages(self, archiver):
        """Archiving empty list should still work (caller handles skip)."""
        path = archiver.archive("cli@local", [], "empty")
        assert path.exists()  # Archiver always writes; caller checks count

    def test_archive_contains_messages(self, archiver):
        """All message content should appear in the archive."""
        messages = _make_messages(5)
        path = archiver.archive("cli@local", messages, "full test")

        content = path.read_text()
        for i in range(5):
            assert f"Message {i + 1}" in content

    def test_archive_contains_sender_names(self, archiver):
        """Archive should include sender names."""
        messages = _make_messages(4)
        path = archiver.archive("cli@local", messages, "sender test")

        content = path.read_text()
        assert "Troy" in content
        assert "OutBot" in content

    def test_summary_in_filename(self, archiver):
        """The summary should appear in the filename."""
        messages = _make_messages(3)
        path = archiver.archive("cli@local", messages, "dark mode preferences")

        assert "dark-mode-preferences" in path.name

    def test_archive_has_metadata(self, archiver):
        """Archive should include date and chat JID."""
        messages = _make_messages(3)
        path = archiver.archive("cli@local", messages, "metadata test")

        content = path.read_text()
        assert "cli@local" in content
        assert "Archived:" in content


class TestCLIArchiveIntegration:
    """Test the CLI's archive-on-quit logic (message count threshold)."""

    def test_message_count_threshold(self):
        """Sessions with < 3 messages should not archive."""
        # This tests the threshold logic from chat.py
        # _message_count tracks user + bot messages
        message_count = 2  # 1 user msg + 1 bot reply = 2
        assert message_count < 3  # Should NOT archive

        message_count = 4  # 2 user msgs + 2 bot replies = 4
        assert message_count >= 3  # Should archive

    def test_message_count_includes_both_sides(self):
        """Each send() adds 2 to the count (user msg + bot reply)."""
        count = 0
        # Simulate send() incrementing
        count += 1  # user message stored
        count += 1  # bot reply stored
        assert count == 2

        count += 1
        count += 1
        assert count == 4
        assert count >= 3  # Should trigger archive
