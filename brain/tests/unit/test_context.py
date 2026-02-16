"""Tests for session context formatting."""

import pytest

from brain.core.models import Message
from brain.session.context import (
    escape_xml,
    format_catchup,
    format_catchup_summary,
)


class TestEscapeXml:
    def test_escapes_ampersand(self):
        assert escape_xml("a & b") == "a &amp; b"

    def test_escapes_angle_brackets(self):
        assert escape_xml("<tag>") == "&lt;tag&gt;"

    def test_escapes_quotes(self):
        assert escape_xml('"hello"') == "&quot;hello&quot;"

    def test_escapes_apostrophe(self):
        assert escape_xml("it's") == "it&apos;s"

    def test_preserves_plain_text(self):
        assert escape_xml("hello world") == "hello world"


class TestFormatCatchup:
    def test_formats_single_message(self):
        msgs = [
            Message(
                id="1",
                chat_jid="test",
                sender="s",
                sender_name="Troy",
                content="hello",
                timestamp="2026-02-15T14:00:00Z",
            )
        ]
        result = format_catchup(msgs)
        assert '<message sender="Troy"' in result
        assert "hello" in result
        assert "<messages>" in result
        assert "</messages>" in result

    def test_formats_multiple_messages(self):
        msgs = [
            Message(
                id="1",
                chat_jid="test",
                sender="s1",
                sender_name="Troy",
                content="hey",
                timestamp="2026-02-15T14:00:00Z",
            ),
            Message(
                id="2",
                chat_jid="test",
                sender="s2",
                sender_name="Sarah",
                content="hi!",
                timestamp="2026-02-15T14:01:00Z",
            ),
        ]
        result = format_catchup(msgs)
        assert "Troy" in result
        assert "Sarah" in result

    def test_empty_messages_returns_empty(self):
        assert format_catchup([]) == ""

    def test_escapes_xml_in_content(self):
        msgs = [
            Message(
                id="1",
                chat_jid="test",
                sender="s",
                sender_name="Troy",
                content="a < b & c > d",
                timestamp="2026-02-15T14:00:00Z",
            )
        ]
        result = format_catchup(msgs)
        assert "&lt;" in result
        assert "&amp;" in result


class TestFormatCatchupSummary:
    def _make_msgs(self, count: int) -> list[Message]:
        return [
            Message(
                id=str(i),
                chat_jid="test",
                sender="s",
                sender_name="Troy",
                content=f"msg {i}",
                timestamp=f"2026-02-15T14:{i % 60:02d}:00Z",
            )
            for i in range(count)
        ]

    def test_small_list_returns_full(self):
        msgs = self._make_msgs(10)
        result = format_catchup_summary(msgs, max_messages=50)
        assert "<gap" not in result

    def test_large_list_truncates_with_gap(self):
        msgs = self._make_msgs(100)
        result = format_catchup_summary(msgs, max_messages=50)
        assert "<gap" in result

    def test_gap_shows_skipped_count(self):
        msgs = self._make_msgs(100)
        result = format_catchup_summary(msgs, max_messages=50)
        # head=5, tail=40, skipped=55
        assert 'count="55"' in result
