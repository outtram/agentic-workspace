"""Tests for periodic reflection and memory evolution."""

import sys
import uuid
from datetime import date

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.core.models import Message
from brain.memory.reflection import (
    _parse_observations,
    _write_observations,
    REFLECTION_SECTION,
)


def _make_messages(count: int) -> list[Message]:
    """Create dummy conversation messages."""
    messages = []
    for i in range(count):
        is_from_me = i % 2 == 1
        messages.append(
            Message(
                id=str(uuid.uuid4()),
                chat_jid="cli@local",
                sender="outbot" if is_from_me else "troy",
                sender_name="OutBot" if is_from_me else "Troy",
                content=f"Test message {i + 1}",
                timestamp=f"2026-02-17T10:{i:02d}:00Z",
                is_from_me=is_from_me,
            )
        )
    return messages


class TestParseObservations:
    def test_parses_simple_lines(self):
        result = "Prefers dark mode\nLikes short responses"
        obs = _parse_observations(result, "")
        assert len(obs) == 2
        assert "Prefers dark mode" in obs
        assert "Likes short responses" in obs

    def test_strips_bullets_and_numbers(self):
        result = "1. Prefers dark mode\n- Likes short answers\n• Works late"
        obs = _parse_observations(result, "")
        assert len(obs) == 3
        assert obs[0] == "Prefers dark mode"
        assert obs[1] == "Likes short answers"
        assert obs[2] == "Works late"

    def test_skips_empty_lines(self):
        result = "\n\nPrefers dark mode\n\n\n"
        obs = _parse_observations(result, "")
        assert len(obs) == 1

    def test_respects_max_observations(self):
        result = "\n".join(f"Observation {i}" for i in range(10))
        obs = _parse_observations(result, "")
        assert len(obs) <= 3  # MAX_OBSERVATIONS = 3

    def test_deduplicates_against_existing(self):
        existing = "## Preferences\n- Prefers dark mode and quiet environments\n"
        result = "Prefers dark mode and quiet environments\nLikes tea"
        obs = _parse_observations(result, existing)
        # "Prefers dark mode" phrase should match existing
        assert not any("dark mode" in o.lower() for o in obs)
        assert any("tea" in o.lower() for o in obs)

    def test_skips_headers(self):
        result = "# Observations\nPrefers dark mode"
        obs = _parse_observations(result, "")
        assert len(obs) == 1
        assert obs[0] == "Prefers dark mode"


class TestWriteObservations:
    def test_creates_section_if_missing(self, tmp_path):
        user_md = tmp_path / "USER.md"
        user_md.write_text("# User Profile\n\n## Preferences\n- Likes coffee\n")

        _write_observations(user_md, ["Prefers dark mode", "Works late"])

        content = user_md.read_text()
        assert REFLECTION_SECTION in content
        assert "Prefers dark mode" in content
        assert "Works late" in content

    def test_appends_to_existing_section(self, tmp_path):
        user_md = tmp_path / "USER.md"
        user_md.write_text(
            f"# User Profile\n\n{REFLECTION_SECTION}\n"
            f"- Existing pattern (observed 2026-02-16)\n"
        )

        _write_observations(user_md, ["New pattern here"])

        content = user_md.read_text()
        assert "Existing pattern" in content
        assert "New pattern here" in content

    def test_includes_date(self, tmp_path):
        user_md = tmp_path / "USER.md"
        user_md.write_text("# User Profile\n")

        _write_observations(user_md, ["Test observation"])

        content = user_md.read_text()
        assert f"observed {date.today().isoformat()}" in content

    def test_preserves_existing_content(self, tmp_path):
        user_md = tmp_path / "USER.md"
        original = "# User Profile\n\n## Preferences\n- Likes coffee\n"
        user_md.write_text(original)

        _write_observations(user_md, ["New observation"])

        content = user_md.read_text()
        assert "Likes coffee" in content
        assert "New observation" in content

    def test_creates_file_if_missing(self, tmp_path):
        user_md = tmp_path / "USER.md"
        assert not user_md.exists()

        _write_observations(user_md, ["First observation"])

        assert user_md.exists()
        content = user_md.read_text()
        assert "First observation" in content
        assert REFLECTION_SECTION in content

    def test_never_overwrites_manual_entries(self, tmp_path):
        """Manual entries in other sections should be untouched."""
        user_md = tmp_path / "USER.md"
        user_md.write_text(
            "# User Profile\n\n"
            "## Communication Style\n- Has ADHD\n- Australian English\n\n"
            "## Preferences\n- Likes coffee\n"
        )

        _write_observations(user_md, ["Works late at night"])

        content = user_md.read_text()
        assert "Has ADHD" in content
        assert "Australian English" in content
        assert "Likes coffee" in content
        assert "Works late at night" in content
