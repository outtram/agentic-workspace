"""Intent router — parses command bar input and routes to handlers."""
from typing import Callable, Awaitable

from . import PROJECT_ROOT
from .brain_logger import log_action
from .cc_logger import logger as cc_log

# Type alias for progress callback
ProgressCallback = Callable[[str], Awaitable[None]]


async def _noop_progress(msg: str) -> None:
    """Default no-op progress callback."""


class Router:
    """Routes command bar input to the right handler."""

    def __init__(self):
        self.claude = None
        self.personality = None
        self._telegram_bridge = None

    def _ensure_brain(self):
        """Lazy-init Claude client and personality loader."""
        if self.claude is None:
            from brain.core.claude_client import ClaudeClient

            self.claude = ClaudeClient()
        if self.personality is None:
            from brain.personality.loader import PersonalityLoader

            self.personality = PersonalityLoader()

    async def route(
        self,
        text: str,
        selected_ids: set[str],
        focused_task: dict | None,
        all_tasks: list[dict],
        today_ids: list[str],
        progress: ProgressCallback | None = None,
    ) -> str:
        """Route input to the right handler and return response text."""
        progress = progress or _noop_progress
        text = text.strip()
        task_ids = self._get_target_ids(selected_ids, focused_task)

        cc_log.debug("ROUTE  %r  task_ids=%s", text, task_ids)
        if text.startswith("/"):
            return await self._handle_slash(
                text, task_ids, all_tasks, today_ids, progress
            )
        else:
            return await self._handle_natural(text, progress, focused_task)

    async def _handle_slash(
        self,
        text: str,
        task_ids: list[str],
        all_tasks: list[dict],
        today_ids: list[str],
        progress: ProgressCallback = _noop_progress,
    ) -> str:
        """Route slash commands to handler functions."""
        from .handlers import triage, enrich, daily_review, research
        from .handlers import email as email_handler
        from .handlers import agent_runner
        from .handlers import memory as memory_handler

        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/done":
            await progress("[dim]Marking done...[/]")
            return await triage.handle_done(task_ids)
        elif cmd == "/today":
            return triage.handle_today(task_ids, today_ids)
        elif cmd == "/remove":
            return triage.handle_remove(task_ids, today_ids)
        elif cmd in ("/q1", "/q2", "/q3", "/q4"):
            await progress(f"[dim]Moving to {cmd[1:].upper()}...[/]")
            return await triage.handle_quadrant(cmd[1:], task_ids)
        elif cmd == "/enrich":
            await progress("[dim]Loading Claude...[/]")
            self._ensure_brain()
            await progress("[dim]Enriching descriptions...[/]")
            return await enrich.handle_enrich(task_ids, all_tasks, self.claude)
        elif cmd == "/research":
            await progress("[dim]Loading Claude...[/]")
            self._ensure_brain()
            return await research.handle_research(
                task_ids, all_tasks, self.claude, progress
            )
        elif cmd in ("/voice", "/v"):
            return "Use [bold]v[/] hotkey to toggle voice mode"
        elif cmd in ("/daily", "/dailyreview", "/daily-review"):
            return await daily_review.handle_daily(progress)
        elif cmd == "/inbox":
            return await email_handler.handle_inbox(progress)
        elif cmd in ("/import-emails", "/import"):
            return await email_handler.handle_import_emails(progress)
        elif cmd == "/email":
            if not args:
                return (
                    "[bold]Usage:[/] /email <message>\n"
                    "Example: /email send Troy a summary of today's Q1 tasks"
                )
            await progress("[dim]Loading Claude...[/]")
            self._ensure_brain()
            return await email_handler.handle_email_send(
                args, self.claude, progress
            )
        elif cmd == "/agent":
            return agent_runner.handle_agents(args)
        elif cmd == "/skill":
            return agent_runner.handle_skills(args)
        elif cmd == "/remember":
            await progress("[dim]Loading Claude...[/]")
            self._ensure_brain()
            await progress("[dim]Saving memory...[/]")
            return await memory_handler.handle_remember(args, self.claude)
        elif cmd == "/forget":
            await progress("[dim]Loading Claude...[/]")
            self._ensure_brain()
            await progress("[dim]Searching memory...[/]")
            return await memory_handler.handle_forget(args, self.claude)
        elif cmd == "/telegram":
            if not args:
                return (
                    "[bold]Usage:[/] /telegram <message>\n"
                    "Sends a message via Telegram to your chat"
                )
            if self._telegram_bridge:
                return await self._telegram_bridge.send(args)
            return "[red]Telegram bridge not running[/]"
        elif cmd == "/arch":
            import subprocess
            arch_path = PROJECT_ROOT / "docs" / "architecture-diagram.html"
            subprocess.Popen(["open", str(arch_path)])
            return "[green]Opened architecture diagram in browser[/]"
        elif cmd == "/help":
            try:
                from .help_gen import generate_help_router, _load_yaml, HELP_DATA
                return generate_help_router(_load_yaml(HELP_DATA))
            except Exception:
                return "[red]Help data unavailable[/]"
        else:
            return f"Unknown command: {cmd}. Type /help for available commands."

    async def _handle_natural(
        self,
        text: str,
        progress: ProgressCallback = _noop_progress,
        focused_task: dict | None = None,
    ) -> str:
        """Send natural language to Claude with personality context."""
        await progress("[dim]Loading personality...[/]")
        self._ensure_brain()

        # Check for memory triggers
        try:
            from brain.memory.remember import (
                is_remember_trigger,
                extract_memory,
                write_memory,
            )

            if is_remember_trigger(text):
                await progress("[dim]Saving memory...[/]")
                memory = await extract_memory(text, self.claude)
                result = write_memory(
                    memory, str(PROJECT_ROOT / ".claude" / "memory")
                )
                return f"[#00D4AA]Remembered:[/] {result}"
        except ImportError:
            pass

        # Build system prompt with personality + task context + recall context
        system = self.personality.load_personality()

        if focused_task:
            tid = focused_task.get("id", "")
            title = focused_task.get("title", "")
            desc = focused_task.get("_description", "")
            quadrant = focused_task.get("eisenhower_quadrant", "")
            status = focused_task.get("status", "")
            task_ctx = f"\n\nCurrent task context:\n- ID: {tid}\n- Title: {title}"
            if desc:
                task_ctx += f"\n- Description: {desc}"
            if quadrant:
                task_ctx += f"\n- Quadrant: {quadrant.upper()}"
            if status:
                task_ctx += f"\n- Status: {status}"
            system += task_ctx

        try:
            from brain.memory.recall import (
                is_recall_trigger,
                search_memory,
                format_recall_context,
            )

            if is_recall_trigger(text):
                await progress("[dim]Checking memory...[/]")
                results = search_memory(
                    text, str(PROJECT_ROOT / ".claude" / "memory")
                )
                recall_ctx = format_recall_context(results)
                if recall_ctx:
                    system += f"\n\n{recall_ctx}"
        except ImportError:
            pass

        await progress("[dim]Asking Claude...[/]")
        try:
            response = await self.claude.ask(text, system_prompt=system)
        except Exception as e:
            return f"[red]Error: {e}[/]"

        await progress("[dim]Formatting response...[/]")
        try:
            from brain.personality.formatter import format_outbound

            return format_outbound(response, channel="cli")
        except ImportError:
            return response

    def _get_target_ids(
        self, selected_ids: set[str], focused_task: dict | None
    ) -> list[str]:
        """Get task IDs to act on — selected or focused."""
        if selected_ids:
            return list(selected_ids)
        if focused_task:
            tid = focused_task.get("id", "")
            return [tid] if tid else []
        return []
