"""Tests for importance judge."""

from unittest.mock import AsyncMock

import pytest

from brain.core.claude_client import ClaudeClient
from brain.heartbeat.judge import ImportanceJudge


def _mock_client(response_text: str) -> ClaudeClient:
    """Create a ClaudeClient with mocked judge method."""
    client = ClaudeClient()
    client.judge = AsyncMock(return_value=response_text)
    return client


class TestImportanceJudge:
    @pytest.mark.asyncio
    async def test_judge_returns_notify(self):
        client = _mock_client(
            '{"should_notify": true, "message": "Meeting in 10 min!", "reasoning": "Imminent meeting"}'
        )
        judge = ImportanceJudge(client=client)

        result = await judge.judge(
            "Meeting with Sarah at 2pm", "Check upcoming meetings"
        )

        assert result.should_notify is True
        assert "Meeting" in result.message

    @pytest.mark.asyncio
    async def test_judge_returns_no_notify(self):
        client = _mock_client(
            '{"should_notify": false, "message": "", "reasoning": "Nothing urgent"}'
        )
        judge = ImportanceJudge(client=client)

        result = await judge.judge("No new reminders", "Check reminders")

        assert result.should_notify is False

    @pytest.mark.asyncio
    async def test_judge_handles_cli_error(self):
        client = ClaudeClient()
        client.judge = AsyncMock(side_effect=Exception("CLI failed"))
        judge = ImportanceJudge(client=client)

        result = await judge.judge("some findings", "some checklist")

        assert result.should_notify is False
        assert "error" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_judge_handles_code_block_wrapped_json(self):
        client = _mock_client(
            '```json\n{"should_notify": true, "message": "Urgent!", "reasoning": "Deadline"}\n```'
        )
        judge = ImportanceJudge(client=client)

        result = await judge.judge("deadline today", "Check deadlines")

        assert result.should_notify is True
        assert result.message == "Urgent!"
