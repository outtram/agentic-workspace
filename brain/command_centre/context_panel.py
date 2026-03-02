"""Right-side context panel — dual-mode: info (today + detail) or chat."""
from datetime import datetime

from textual.containers import VerticalScroll
from textual.widgets import Input, Static

from .sanitiser import sanitise
from .skill_matcher import match_for_task
from .task_loader import QUADRANT_COLOURS, QUADRANT_LABELS

# Max chat messages to keep in memory
_MAX_CHAT_MESSAGES = 50


class ContextPanel(VerticalScroll):
    """Dual-mode panel: info (today shortlist + detail) or chat (conversation)."""

    DEFAULT_CSS = """
    ContextPanel {
        width: 1fr;
        min-width: 28;
        border-left: solid #333333;
        padding: 1 2;
    }
    #panel-content {
        width: 100%;
    }
    #chat-header {
        width: 100%;
        display: none;
    }
    #chat-history {
        height: 1fr;
        min-height: 10;
        display: none;
        scrollbar-size: 1 1;
    }
    #chat-messages {
        width: 100%;
    }
    #chat-input {
        display: none;
        margin-top: 1;
        background: #222222;
        border: solid #333333;
    }
    #chat-input:focus {
        border: solid #FF6B35;
        background: #2a2a2a;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mode: str = "info"  # "info" | "chat"
        self._chat_history: list[tuple[str, str, str]] = []  # (role, content, timestamp)
        self._task_context: list[dict] = []  # currently selected/focused tasks

    def compose(self):
        yield Static(id="panel-content")
        yield Static(id="chat-header")
        with VerticalScroll(id="chat-history"):
            yield Static(id="chat-messages")
        yield Input(placeholder="Chat with OutBot...", id="chat-input")

    @property
    def is_chat_mode(self) -> bool:
        return self._mode == "chat"

    def toggle_mode(self):
        """Switch between info and chat modes."""
        if self._mode == "info":
            self._mode = "chat"
        else:
            self._mode = "info"
        self._apply_mode_visibility()

    def _apply_mode_visibility(self):
        """Toggle widget visibility based on current mode."""
        try:
            panel_content = self.query_one("#panel-content", Static)
            chat_header = self.query_one("#chat-header", Static)
            chat_history = self.query_one("#chat-history", VerticalScroll)
            chat_input = self.query_one("#chat-input", Input)

            if self._mode == "chat":
                panel_content.styles.display = "none"
                chat_header.styles.display = "block"
                chat_history.styles.display = "block"
                chat_input.styles.display = "block"
                # Update chat header and messages
                self._render_chat_header()
                self._render_chat_messages()
                # Focus the chat input
                chat_input.focus()
            else:
                panel_content.styles.display = "block"
                chat_header.styles.display = "none"
                chat_history.styles.display = "none"
                chat_input.styles.display = "none"
        except Exception:
            pass

    def set_task_context(self, tasks: list[dict]):
        """Update the context badge with selected/focused tasks."""
        self._task_context = tasks
        if self._mode == "chat":
            self._render_chat_header()

    def add_chat_message(self, role: str, content: str):
        """Append a message to chat history and re-render."""
        ts = datetime.now().strftime("%H:%M")
        self._chat_history.append((role, content, ts))
        # Trim to max
        if len(self._chat_history) > _MAX_CHAT_MESSAGES:
            self._chat_history = self._chat_history[-_MAX_CHAT_MESSAGES:]
        if self._mode == "chat":
            self._render_chat_messages()

    def add_system_message(self, content: str):
        """Add a system message (e.g. from heartbeat)."""
        self.add_chat_message("system", content)

    def _render_chat_header(self):
        """Render the context badge at the top of chat mode."""
        try:
            header = self.query_one("#chat-header", Static)
        except Exception:
            return

        lines = "[bold #FF6B35]CHAT[/]\n"
        lines += "[#333333]" + "\u2501" * 24 + "[/]\n"

        if self._task_context:
            ids = [t.get("id", "?") for t in self._task_context if t.get("id")]
            if ids:
                id_str = ", ".join(ids[:5])
                if len(ids) > 5:
                    id_str += f" +{len(ids) - 5}"
                lines += f"[dim]Context: {id_str}[/]\n"

                # Show first task title if only one
                if len(self._task_context) == 1:
                    title = sanitise(self._task_context[0].get("title", "")).replace("[", r"\[")
                    if len(title) > 30:
                        title = title[:27] + "..."
                    lines += f"[dim]{title}[/]\n"
        else:
            lines += "[dim]No task selected[/]\n"

        header.update(lines)

    def _render_chat_messages(self):
        """Render the chat message history."""
        try:
            messages = self.query_one("#chat-messages", Static)
            history = self.query_one("#chat-history", VerticalScroll)
        except Exception:
            return

        if not self._chat_history:
            messages.update("[dim]Start chatting with OutBot...[/]\n[dim]Type below or press c to switch back[/]")
            return

        lines: list[str] = []
        for role, content, ts in self._chat_history:
            if role == "user":
                lines.append(f"[dim]{ts}[/] [bold #00D4AA]You:[/] {content}")
            elif role == "assistant":
                lines.append(f"[dim]{ts}[/] [bold #FF6B35]OutBot:[/] {content}")
            elif role == "system":
                lines.append(f"[dim]{ts}[/] [bold yellow]\u26a1[/] {content}")

        messages.update("\n\n".join(lines))

        # Auto-scroll to bottom
        try:
            history.scroll_end(animate=False)
        except Exception:
            pass

    # --- Info mode methods (unchanged) ---

    def update_content(
        self,
        today_ids: list[str],
        all_tasks: list[dict],
        focused_task: dict | None = None,
        response: str = "",
    ):
        """Refresh panel content (info mode only)."""
        if self._mode == "chat":
            return  # Don't overwrite chat view

        content = self._render_today(today_ids, all_tasks)
        if response:
            content += "\n" + self._render_response(response)
        elif focused_task:
            content += "\n" + self._render_detail(focused_task, all_tasks)
        try:
            self.query_one("#panel-content", Static).update(content)
        except Exception:
            pass

    def _render_today(self, today_ids: list[str], all_tasks: list[dict]) -> str:
        """Render the today shortlist."""
        count = len(today_ids)
        lines = f"[bold #00D4AA]TODAY[/] [dim]({count} task{'s' if count != 1 else ''})[/]\n"
        lines += "[#333333]" + "\u2501" * 24 + "[/]\n"

        if not today_ids:
            lines += "[dim](none yet)[/]\n"
            lines += "[dim]Press t to add tasks[/]\n"
        else:
            task_map = {t["id"]: t for t in all_tasks if "id" in t}
            for tid in today_ids:
                t = task_map.get(tid)
                if t:
                    q = t.get("eisenhower_quadrant", "q4")
                    colour = QUADRANT_COLOURS.get(q, "#3D3D3D")
                    name = sanitise(t.get("title", tid)).replace("[", r"\[")
                    if len(name) > 24:
                        name = name[:21] + "..."
                    lines += f"[{colour}]\u25cf[/] {name}\n"
                else:
                    lines += f"[dim]\u25cb {tid}[/]\n"

        return lines

    def _render_response(self, response: str) -> str:
        """Render OutBot response."""
        lines = "\n[bold #FF6B35]OUTBOT[/]\n"
        lines += "[#333333]" + "\u2501" * 24 + "[/]\n"
        lines += response
        return lines

    def _render_detail(self, task: dict, all_tasks: list[dict] | None = None) -> str:
        """Render focused task detail."""
        lines = "\n[bold]DETAIL[/]\n"
        lines += "[#333333]" + "\u2501" * 24 + "[/]\n"

        title = sanitise(task.get("title", "Untitled")).replace("[", r"\[")
        out_id = task.get("id", "???")
        q = task.get("eisenhower_quadrant", "q4")
        colour = QUADRANT_COLOURS.get(q, "#3D3D3D")
        label = QUADRANT_LABELS.get(q, "Q4")

        lines += f"[{colour}]{label}[/]\n"
        lines += f"[bold]{title}[/]\n"
        lines += f"[dim]{out_id}[/]\n"

        if "_due_date" in task:
            due_str = task["_due_date"].strftime("%d %b %Y")
            if task.get("_overdue"):
                lines += f"[bold red]OVERDUE: {due_str}[/]\n"
            else:
                lines += f"[dim]Due: {due_str}[/]\n"

        priority = task.get("priority", "low")
        if priority != "low":
            lines += f"[dim]Priority: {priority}[/]\n"

        parent = task.get("parent")
        if parent:
            parent_title = ""
            if all_tasks:
                for t in all_tasks:
                    if t.get("id") == parent:
                        parent_title = sanitise(
                            t.get("title", "")
                        ).replace("[", r"\[")
                        break
            if parent_title:
                lines += f"[dim]\u2191 Parent: {parent} — {parent_title}[/]\n"
            else:
                lines += f"[dim]\u2191 Parent: {parent}[/]\n"

        children = task.get("children", [])
        if children:
            lines += f"[dim]\u25bc {len(children)} subtask{'s' if len(children) != 1 else ''}:[/]\n"
            for child_id in children[:5]:
                child_title = ""
                if all_tasks:
                    for t in all_tasks:
                        if t.get("id") == child_id:
                            child_title = sanitise(
                                t.get("title", "")
                            ).replace("[", r"\[")
                            break
                if child_title:
                    lines += f"  [dim]{child_id}: {child_title[:30]}[/]\n"
                else:
                    lines += f"  [dim]{child_id}[/]\n"
            if len(children) > 5:
                lines += f"  [dim]... +{len(children) - 5} more[/]\n"

        desc = sanitise(task.get("_description", "")).replace("[", r"\[")
        if desc:
            lines += f"\n{desc[:300]}\n"
            if len(desc) > 300:
                lines += "[dim]...[/]\n"

        # Actions hint
        lines += "\n[bold]ACTIONS[/]\n"
        lines += "[#333333]" + "\u2501" * 24 + "[/]\n"
        lines += "[dim]/enrich  /research  /done[/]\n"
        lines += "[dim]e Edit  t Today  [bold #FF6B35]/ Commands[/][/]\n"

        # Contextual suggestions
        suggestions = match_for_task(task)
        if suggestions["agents"] or suggestions["skills"]:
            lines += "\n[bold]Suggested[/]\n"
            for a in suggestions["agents"][:2]:
                lines += f"[#00D4AA]{a['name']}[/] [dim]{a['desc']}[/]\n"
            for s in suggestions["skills"][:2]:
                lines += f"[#00D4AA]{s['name']}[/] [dim]{s['desc']}[/]\n"

        return lines
