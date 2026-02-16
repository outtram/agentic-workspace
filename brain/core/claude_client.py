"""Claude client that uses the Claude Code CLI (Max plan) instead of the API.

This avoids needing a separate API key - OutBot piggybacks on Troy's
Anthropic Max subscription via the `claude` CLI in non-interactive mode.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)

# Default model for chat responses
CHAT_MODEL = "sonnet"
# Cheaper/faster model for importance judging
JUDGE_MODEL = "haiku"


class ClaudeClient:
    """Async wrapper around `claude --print` CLI for LLM calls."""

    def __init__(self, model: str = CHAT_MODEL) -> None:
        self.model = model

    async def ask(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str | None = None,
        max_tokens: int | None = None,
        output_json: bool = False,
    ) -> str:
        """Send a prompt to Claude via CLI and return the response text.

        Args:
            prompt: The user message to send.
            system_prompt: Optional system prompt.
            model: Override the default model (e.g. "haiku", "opus").
            max_tokens: Not directly supported by CLI, ignored.
            output_json: If True, request JSON output format.

        Returns:
            The response text from Claude.
        """
        cmd = [
            "claude",
            "--print",
            "--model", model or self.model,
            "--no-session-persistence",
            "--dangerously-skip-permissions",
        ]

        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        if output_json:
            cmd.extend(["--output-format", "json"])

        # Prompt goes last
        cmd.append(prompt)

        # Unset CLAUDECODE env var to allow nested invocation
        env = {**os.environ}
        env.pop("CLAUDECODE", None)

        logger.debug("Claude CLI call: model=%s, prompt=%d chars", model or self.model, len(prompt))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=120
            )

            if proc.returncode != 0:
                err_msg = stderr.decode("utf-8", errors="replace").strip()
                logger.error("Claude CLI failed (rc=%d): %s", proc.returncode, err_msg)
                raise RuntimeError(f"Claude CLI error: {err_msg}")

            result = stdout.decode("utf-8", errors="replace").strip()

            if output_json:
                # Parse the JSON output to extract the result text
                try:
                    data = json.loads(result)
                    return data.get("result", result)
                except json.JSONDecodeError:
                    return result

            return result

        except asyncio.TimeoutError:
            logger.error("Claude CLI timed out after 120s")
            raise RuntimeError("Claude CLI timed out")

    async def judge(
        self,
        prompt: str,
        system_prompt: str = "",
    ) -> str:
        """Quick Claude call using a fast/cheap model for judging tasks."""
        return await self.ask(
            prompt=prompt,
            system_prompt=system_prompt,
            model=JUDGE_MODEL,
        )
