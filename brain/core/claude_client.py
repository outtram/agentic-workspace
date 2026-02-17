"""Claude client that uses the Claude Code CLI (Max plan) instead of the API.

This avoids needing a separate API key - OutBot piggybacks on Troy's
Anthropic Max subscription via the `claude` CLI in non-interactive mode.
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)

# Default model for chat responses
CHAT_MODEL = "sonnet"
# Cheaper/faster model for importance judging
JUDGE_MODEL = "haiku"


def _find_claude() -> str:
    """Find the claude CLI binary."""
    path = shutil.which("claude")
    if path:
        return path
    # Common install locations
    for candidate in [
        os.path.expanduser("~/.local/bin/claude"),
        "/usr/local/bin/claude",
    ]:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return "claude"  # Fall back, let subprocess raise the error


def _run_claude(cmd: list[str], env: dict) -> tuple[str, str, int]:
    """Run claude CLI synchronously. Called from a thread."""
    result = subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=180,
    )
    return (
        result.stdout.decode("utf-8", errors="replace").strip(),
        result.stderr.decode("utf-8", errors="replace").strip(),
        result.returncode,
    )


class ClaudeClient:
    """Wrapper around `claude --print` CLI for LLM calls."""

    def __init__(self, model: str = CHAT_MODEL) -> None:
        self.model = model
        self._claude_path = _find_claude()
        logger.debug("Claude CLI path: %s", self._claude_path)

    async def ask(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str | None = None,
        max_tokens: int | None = None,
        output_json: bool = False,
    ) -> str:
        """Send a prompt to Claude via CLI and return the response text."""
        cmd = [
            self._claude_path,
            "--print",
            "--model", model or self.model,
            "--no-session-persistence",
            "--dangerously-skip-permissions",
        ]

        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        if output_json:
            cmd.extend(["--output-format", "json"])

        # Prompt as positional argument
        cmd.append(prompt)

        # Clean environment for nested invocation
        env = {**os.environ}
        env.pop("CLAUDECODE", None)
        env.pop("CLAUDE_CODE_ENTRYPOINT", None)

        logger.debug(
            "Claude CLI call: model=%s, prompt=%d chars, system=%d chars",
            model or self.model, len(prompt), len(system_prompt),
        )

        loop = asyncio.get_running_loop()
        try:
            stdout_text, stderr_text, rc = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    functools.partial(_run_claude, cmd, env),
                ),
                timeout=190,  # Slightly above subprocess.run's 180s
            )
        except (asyncio.TimeoutError, subprocess.TimeoutExpired):
            logger.error("Claude CLI timed out after 180s")
            raise RuntimeError(
                "Claude CLI timed out — is `claude` authenticated in your terminal?"
            )

        if stderr_text:
            for line in stderr_text.splitlines():
                logger.debug("Claude CLI stderr: %s", line)

        if rc != 0:
            logger.error("Claude CLI failed (rc=%d): %s", rc, stderr_text)
            raise RuntimeError(f"Claude CLI error (rc={rc}): {stderr_text}")

        if output_json:
            try:
                data = json.loads(stdout_text)
                return data.get("result", stdout_text)
            except json.JSONDecodeError:
                return stdout_text

        return stdout_text

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
