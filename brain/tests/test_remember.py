"""Tests for the remember/forget memory module."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.memory.remember import (
    is_remember_trigger,
    is_forget_trigger,
    is_memory_trigger,
    write_memory,
)
from pathlib import Path


class TestRememberTrigger:
    def test_detects_remember_triggers(self):
        assert is_remember_trigger("remember I hate standups")
        assert is_remember_trigger("Remember that I prefer dark mode")
        assert is_remember_trigger("don't forget I'm allergic to shellfish")
        assert is_remember_trigger("note that the deploy key is ABC123")
        assert is_remember_trigger("keep in mind I work from home on Fridays")

    def test_ignores_non_triggers(self):
        assert not is_remember_trigger("what do you remember?")
        assert not is_remember_trigger("do you remember when we deployed?")
        assert not is_remember_trigger("can you remember that?")
        assert not is_remember_trigger("how do I configure the server?")
        assert not is_remember_trigger("tell me about the deploy process")

    def test_ignores_recall_questions(self):
        """Questions about existing memories should NOT trigger storage."""
        assert not is_remember_trigger("what do you remember about me?")
        assert not is_remember_trigger("do you remember my favourite colour?")

    def test_case_insensitive(self):
        assert is_remember_trigger("REMEMBER I like tea")
        assert is_remember_trigger("Remember I prefer vim")


class TestForgetTrigger:
    def test_detects_forget_triggers(self):
        assert is_forget_trigger("forget that I hate standups")
        assert is_forget_trigger("stop remembering my server IP")
        assert is_forget_trigger("remove the memory about dark mode")

    def test_ignores_non_forget(self):
        assert not is_forget_trigger("remember I like coffee")
        assert not is_forget_trigger("what did I say earlier?")


class TestMemoryTrigger:
    def test_detects_either(self):
        assert is_memory_trigger("remember I like tea")
        assert is_memory_trigger("forget about the server IP")
        assert not is_memory_trigger("what's the weather?")


class TestWriteMemory:
    def test_write_user_pref_appends_to_user_md(self, tmp_path):
        """Writing a user_pref should append to USER.md."""
        user_md = tmp_path / "USER.md"
        user_md.write_text("# User Profile\n\n## Preferences\n- Likes coffee\n")

        entry = {"content": "Hates morning meetings", "category": "user_pref"}
        write_memory(entry, str(tmp_path))

        content = user_md.read_text()
        assert "Hates morning meetings" in content
        assert "## Learned" in content

    def test_write_fact_creates_learned_md(self, tmp_path):
        """Writing a fact should go to LEARNED.md."""
        entry = {"content": "Server IP is 10.0.0.5", "category": "fact"}
        write_memory(entry, str(tmp_path))

        learned = tmp_path / "LEARNED.md"
        assert learned.exists()
        content = learned.read_text()
        assert "Server IP is 10.0.0.5" in content

    def test_write_memory_creates_learned_section(self, tmp_path):
        """Should create ## Learned section in USER.md if missing."""
        user_md = tmp_path / "USER.md"
        user_md.write_text("# User Profile\n\n## Preferences\n- Likes coffee\n")

        entry = {"content": "Prefers dark mode", "category": "user_pref"}
        write_memory(entry, str(tmp_path))

        content = user_md.read_text()
        assert "## Learned" in content
        assert "Prefers dark mode" in content

    def test_write_memory_appends_multiple(self, tmp_path):
        """Multiple writes should all appear in the file."""
        entries = [
            {"content": "Likes tea", "category": "user_pref"},
            {"content": "Hates standups", "category": "user_pref"},
        ]
        for e in entries:
            write_memory(e, str(tmp_path))

        content = (tmp_path / "USER.md").read_text()
        assert "Likes tea" in content
        assert "Hates standups" in content

    def test_write_memory_includes_date(self, tmp_path):
        """Memory entries should include the learned date."""
        from datetime import date

        entry = {"content": "Test memory", "category": "fact"}
        write_memory(entry, str(tmp_path))

        content = (tmp_path / "LEARNED.md").read_text()
        assert f"learned {date.today().isoformat()}" in content


class TestForgetMemory:
    """Forget tests that don't require Claude (file operations only)."""

    def test_direct_line_removal(self, tmp_path):
        """Test that we can remove a line matching a search term."""
        from brain.memory.remember import _append_to_learned

        learned = tmp_path / "LEARNED.md"
        _append_to_learned(learned, "fact", "- Server IP is 10.0.0.5 (learned 2026-02-17)")
        _append_to_learned(learned, "fact", "- Deploy key is ABC123 (learned 2026-02-17)")

        content = learned.read_text()
        assert "Server IP" in content
        assert "Deploy key" in content

        # Simulate forget by removing matching line
        lines = content.splitlines()
        new_lines = [l for l in lines if "server ip" not in l.lower()]
        learned.write_text("\n".join(new_lines) + "\n")

        content = learned.read_text()
        assert "Server IP" not in content
        assert "Deploy key" in content
