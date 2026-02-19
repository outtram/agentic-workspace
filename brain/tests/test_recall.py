"""Tests for memory recall from past conversations."""

import sys
import uuid

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.memory.recall import (
    is_recall_trigger,
    search_memory,
    format_recall_context,
    _extract_keywords,
)


class TestRecallTrigger:
    def test_detects_recall_triggers(self):
        assert is_recall_trigger("what did we discuss last time?")
        assert is_recall_trigger("remember when we fixed that SSL issue?")
        assert is_recall_trigger("last session we talked about voice")
        assert is_recall_trigger("you told me to use haiku for judging")
        assert is_recall_trigger("we discussed the archiver previously")
        assert is_recall_trigger("what do you know about my preferences?")

    def test_ignores_non_recall(self):
        assert not is_recall_trigger("remember I like dark mode")
        assert not is_recall_trigger("how do I fix this bug?")
        assert not is_recall_trigger("what's the weather today?")
        assert not is_recall_trigger("earlier today I was coding")

    def test_case_insensitive(self):
        assert is_recall_trigger("LAST TIME we talked about this")
        assert is_recall_trigger("Remember When we deployed?")


class TestExtractKeywords:
    def test_removes_stop_words(self):
        kws = _extract_keywords("what did we discuss about the SSL certificate issue?")
        assert "ssl" in kws
        assert "certificate" in kws
        assert "issue" in kws
        assert "what" not in kws
        assert "the" not in kws

    def test_preserves_order(self):
        kws = _extract_keywords("voice recording module not working")
        assert kws.index("voice") < kws.index("recording")

    def test_deduplicates(self):
        kws = _extract_keywords("test the test runner test")
        assert kws.count("test") == 1


class TestSearchMemory:
    def test_searches_memory_files(self, tmp_path):
        """Should find content in memory .md files."""
        # Create a memory file with searchable content
        user_md = tmp_path / "USER.md"
        user_md.write_text("## Preferences\n- Hates morning meetings\n- Likes dark mode\n")

        # Use tmp_path for conversations too, to isolate from real data
        conv_dir = tmp_path / "convos"
        conv_dir.mkdir()
        results = search_memory("morning meetings", str(tmp_path), str(conv_dir))
        assert len(results) >= 1
        assert any("morning" in r["snippet"].lower() for r in results)

    def test_returns_empty_for_no_match(self, tmp_path):
        user_md = tmp_path / "USER.md"
        user_md.write_text("## Preferences\n- Likes coffee\n")

        conv_dir = tmp_path / "convos"
        conv_dir.mkdir()
        results = search_memory("dinosaurs in space", str(tmp_path), str(conv_dir))
        assert len(results) == 0

    def test_searches_conversation_archives(self, tmp_path):
        """Should find content in conversation archive files."""
        conv_dir = tmp_path / "conversations"
        conv_dir.mkdir()
        archive = conv_dir / "2026-02-17-ssl-debugging.md"
        archive.write_text(
            "# SSL Debugging\n\n"
            "**Troy:** The SSL certs are broken again\n"
            "**OutBot:** Let me check the CA bundle\n"
        )

        results = search_memory("SSL certs", str(tmp_path), str(conv_dir))
        assert len(results) >= 1
        assert any("SSL" in r["snippet"] for r in results)


class TestFormatRecallContext:
    def test_formats_as_xml(self):
        results = [
            {"file": "/path/to/2026-02-17-chat.md", "snippet": "We discussed SSL certs"},
            {"file": "/path/to/USER.md", "snippet": "- Likes dark mode"},
        ]
        output = format_recall_context(results)
        assert "<memory_recall>" in output
        assert "</memory_recall>" in output
        assert "SSL certs" in output
        assert "dark mode" in output

    def test_empty_results_returns_empty(self):
        assert format_recall_context([]) == ""

    def test_includes_filename(self):
        results = [{"file": "/path/to/2026-02-17-ssl-debug.md", "snippet": "cert issue"}]
        output = format_recall_context(results)
        assert "2026-02-17-ssl-debug.md" in output

    def test_respects_max_chars(self):
        """Should truncate if results exceed MAX_RECALL_CHARS."""
        results = [
            {"file": f"/path/{i}.md", "snippet": "x" * 1000}
            for i in range(10)
        ]
        output = format_recall_context(results)
        # Should be under ~4200 chars (4000 + XML tags + filenames)
        assert len(output) < 5000
