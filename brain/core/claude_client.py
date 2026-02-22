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
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Default model for chat responses — override with OUTBOT_CHAT_MODEL env var
# Options: "opus" (smartest), "sonnet" (balanced), "haiku" (fastest/cheapest)
CHAT_MODEL = os.environ.get("OUTBOT_CHAT_MODEL", "opus")
# Model for background tasks (memory, judging, summaries) — override with OUTBOT_JUDGE_MODEL
JUDGE_MODEL = os.environ.get("OUTBOT_JUDGE_MODEL", "sonnet")

# Cached path to combined CA certs (for corporate proxies)
_ca_certs_path: str | None = None


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


def _get_ca_certs() -> str:
    """Get path to CA cert bundle that includes macOS system + corporate certs.

    The claude CLI (Node.js) doesn't trust corporate proxy CAs by default.
    This exports them from the macOS keychain and combines with the system roots.
    """
    global _ca_certs_path
    if _ca_certs_path and os.path.exists(_ca_certs_path):
        return _ca_certs_path

    combined = Path(tempfile.gettempdir()) / "outbot_node_certs.pem"
    if combined.exists() and combined.stat().st_size > 1000:
        _ca_certs_path = str(combined)
        return _ca_certs_path

    logger.debug("Building CA cert bundle for Node.js...")
    certs = []
    for keychain in [
        "/System/Library/Keychains/SystemRootCertificates.keychain",
        "/Library/Keychains/System.keychain",
    ]:
        try:
            result = subprocess.run(
                ["security", "find-certificate", "-a", "-p", keychain],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                certs.append(result.stdout)
        except Exception:
            pass

    if certs:
        combined.write_text("\n".join(certs))
        _ca_certs_path = str(combined)
        logger.debug("CA cert bundle: %s (%d bytes)", _ca_certs_path, combined.stat().st_size)
    else:
        logger.warning("Could not export macOS certificates")
        _ca_certs_path = ""

    return _ca_certs_path


def _run_claude(cmd: list[str], env: dict, stdin_text: str = "") -> tuple[str, str, int]:
    """Run claude CLI synchronously. Called from a thread.

    Pipes the prompt via stdin because some claude CLI versions hang
    when the prompt is passed as a positional argument.
    """
    result = subprocess.run(
        cmd,
        input=stdin_text.encode("utf-8") if stdin_text else None,
        stdin=subprocess.DEVNULL if not stdin_text else subprocess.PIPE,
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
        self._usage_tracker = None
        logger.debug("Claude CLI path: %s", self._claude_path)

    def set_usage_tracker(self, tracker):
        """Attach a UsageTracker to record token consumption."""
        self._usage_tracker = tracker

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
            "--output-format", "json",
        ]

        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        # Pipe prompt via stdin (positional arg hangs on some CLI versions)
        stdin_text = prompt

        # Clean environment for nested invocation
        env = {**os.environ}
        env.pop("CLAUDECODE", None)
        env.pop("CLAUDE_CODE_ENTRYPOINT", None)

        # Fix corporate proxy SSL: tell Node.js to trust macOS system certs
        if "NODE_EXTRA_CA_CERTS" not in env:
            ca_path = _get_ca_certs()
            if ca_path:
                env["NODE_EXTRA_CA_CERTS"] = ca_path

        logger.debug(
            "Claude CLI call: model=%s, prompt=%d chars, system=%d chars",
            model or self.model, len(prompt), len(system_prompt),
        )

        loop = asyncio.get_running_loop()
        try:
            stdout_text, stderr_text, rc = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    functools.partial(_run_claude, cmd, env, stdin_text),
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

        # Always parse JSON to extract result + usage
        try:
            data = json.loads(stdout_text)
            result_text = data.get("result", stdout_text)

            # Record usage if tracker attached
            if self._usage_tracker and "usage" in data:
                cost = data.get("total_cost_usd", 0.0)
                self._usage_tracker.record(data["usage"], cost)

            return result_text
        except json.JSONDecodeError:
            # Fallback: return raw text if JSON parsing fails
            logger.warning("Failed to parse JSON output, returning raw text")
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
