"""Intent router — parses command bar input and routes to handlers."""
from typing import Callable, Awaitable

from . import PROJECT_ROOT
from .brain_logger import log_action

# Type alias for progress callback
ProgressCallback = Callable[[str], Awaitable[None]]


async def _noop_progress(msg: str) -> None:
    """Default no-op progress callback."""


class Router:
    """Routes command bar input to the right handler."""

    def __init__(self):
        self.claude = None
        self.personality = None

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

        if text.startswith("/"):
            return await self._handle_slash(
                text, task_ids, all_tasks, today_ids, progress
            )
        else:
            return await self._handle_natural(text, progress)

    async def _handle_slash(
        self,
        text: str,
        task_ids: list[str],
        all_tasks: list[dict],
        today_ids: list[str],
        progress: ProgressCallback = _noop_progress,
    ) -> str:
        """Route slash commands to handler functions."""
        from .handlers import triage, enrich, daily_review

        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()

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
        elif cmd == "/daily":
            await progress("[dim]Running daily review...[/]")
            return await daily_review.handle_daily()
        elif cmd == "/help":
            return (
                "[bold]Commands:[/] /done /today /remove "
                "/q1 /q2 /q3 /q4 /enrich /daily /help\n"
                "[bold]Filters:[/] :q1 :overdue :today :search term\n"
                "[bold]Natural language:[/] Just type to talk to OutBot"
            )
        else:
            return f"Unknown command: {cmd}. Type /help for available commands."

    async def _handle_natural(
        self,
        text: str,
        progress: ProgressCallback = _noop_progress,
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

        # Build system prompt with personality + recall context
        system = self.personality.load_personality()

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
