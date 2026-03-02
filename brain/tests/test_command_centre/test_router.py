"""Test the Command Centre router handles all slash commands correctly."""

import pytest

from brain.command_centre.router import Router


@pytest.fixture
def router():
    return Router()


@pytest.fixture
def empty_context():
    """Minimal context for routing tests."""
    return {
        "selected_ids": set(),
        "focused_task": None,
        "all_tasks": [],
        "today_ids": [],
    }


class TestSlashCommandRouting:
    """Verify every documented slash command is routed without crashing."""

    async def _route(self, router, cmd, ctx):
        return await router.route(
            cmd,
            ctx["selected_ids"],
            ctx["focused_task"],
            ctx["all_tasks"],
            ctx["today_ids"],
        )

    @pytest.mark.asyncio
    async def test_help_returns_content(self, router, empty_context):
        """'/help' should return help text without errors."""
        result = await self._route(router, "/help", empty_context)
        assert "Slash Commands" in result
        assert "/done" in result

    @pytest.mark.asyncio
    async def test_unknown_command_returns_error(self, router, empty_context):
        """Unknown commands should return a helpful error."""
        result = await self._route(router, "/nonexistent", empty_context)
        assert "Unknown command" in result
        assert "/help" in result

    @pytest.mark.asyncio
    async def test_done_with_no_selection(self, router, empty_context):
        """'/done' with no tasks selected should handle gracefully."""
        result = await self._route(router, "/done", empty_context)
        # Should not raise — may return empty result or a message
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_today_with_no_selection(self, router, empty_context):
        """'/today' with no tasks selected should handle gracefully."""
        result = await self._route(router, "/today", empty_context)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_voice_shortcut(self, router, empty_context):
        """'/voice' should return guidance about the hotkey."""
        result = await self._route(router, "/voice", empty_context)
        assert "v" in result.lower()

    @pytest.mark.asyncio
    async def test_email_without_args(self, router, empty_context):
        """'/email' without args should show usage."""
        result = await self._route(router, "/email", empty_context)
        assert "Usage" in result

    @pytest.mark.asyncio
    async def test_telegram_without_args(self, router, empty_context):
        """'/telegram' without args should show usage."""
        result = await self._route(router, "/telegram", empty_context)
        assert "Usage" in result


class TestCommandParsing:
    """Verify command parsing edge cases."""

    async def _route(self, router, cmd, ctx):
        return await router.route(
            cmd,
            ctx["selected_ids"],
            ctx["focused_task"],
            ctx["all_tasks"],
            ctx["today_ids"],
        )

    @pytest.mark.asyncio
    async def test_case_insensitive(self, router, empty_context):
        """Commands should be case-insensitive."""
        result = await self._route(router, "/HELP", empty_context)
        assert "Slash Commands" in result

    @pytest.mark.asyncio
    async def test_whitespace_trimmed(self, router, empty_context):
        """Leading/trailing whitespace should be trimmed."""
        result = await self._route(router, "  /help  ", empty_context)
        assert "Slash Commands" in result
