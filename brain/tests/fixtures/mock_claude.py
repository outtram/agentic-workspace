"""Mock Claude client for testing (replaces real CLI calls)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

from brain.core.claude_client import ClaudeClient


def make_mock_claude(response_text: str = "G'day! How can I help?") -> ClaudeClient:
    """Create a mock ClaudeClient that returns a canned response.

    Usage:
        mock_client = make_mock_claude("Here's your answer")
        result = await mock_client.ask("What's up?")
        assert result == "Here's your answer"
    """
    client = ClaudeClient()
    client.ask = AsyncMock(return_value=response_text)
    client.judge = AsyncMock(return_value=response_text)
    return client


def make_mock_judge_response(
    should_notify: bool = False,
    message: str = "",
    reasoning: str = "Nothing urgent",
) -> ClaudeClient:
    """Create a mock ClaudeClient that returns a judge-formatted JSON response."""
    response_json = json.dumps(
        {
            "should_notify": should_notify,
            "message": message,
            "reasoning": reasoning,
        }
    )
    return make_mock_claude(response_json)
