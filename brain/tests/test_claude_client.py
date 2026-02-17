"""Tests for Claude CLI client — the Max plan workaround."""

import asyncio
import sys

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.core.claude_client import ClaudeClient, CHAT_MODEL, JUDGE_MODEL


class TestClaudeClient:
    def test_default_model(self):
        client = ClaudeClient()
        assert client.model == CHAT_MODEL

    def test_custom_model(self):
        client = ClaudeClient(model="haiku")
        assert client.model == "haiku"

    def test_model_constants(self):
        assert CHAT_MODEL == "sonnet"
        assert JUDGE_MODEL == "haiku"


class TestClaudeClientLive:
    """Live tests that actually call claude --print. Slow but essential."""

    @pytest.mark.slow
    def test_basic_ask(self):
        client = ClaudeClient()
        reply = asyncio.run(client.ask(
            prompt="Reply with exactly: PONG",
            system_prompt="You are a test bot. Reply only with what is asked.",
        ))
        assert "PONG" in reply

    @pytest.mark.slow
    def test_ask_with_system_prompt(self):
        client = ClaudeClient()
        reply = asyncio.run(client.ask(
            prompt="What is your name?",
            system_prompt="Your name is OutBot. Reply in 5 words or less.",
        ))
        assert "OutBot" in reply or "outbot" in reply.lower()

    @pytest.mark.slow
    def test_judge_uses_haiku(self):
        client = ClaudeClient()
        reply = asyncio.run(client.judge(
            prompt="Reply with exactly: JUDGED",
            system_prompt="You are a test bot.",
        ))
        assert "JUDGED" in reply
