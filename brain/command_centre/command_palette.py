"""Command Palette — navigable list of commands, agents, and skills.

Triggered by / key. Shows contextual suggestions, slash commands, agents,
and skills in a filterable, keyboard-navigable list.
"""

from textual import events
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from .skill_matcher import match_for_task


# All slash commands
_COMMANDS = [
    ("/done", "Mark selected tasks done"),
    ("/today", "Add selected to today"),
    ("/remove", "Remove from today"),
    ("/q1", "Move to Q1 (urgent + important)"),
    ("/q2", "Move to Q2 (important)"),
    ("/q3", "Move to Q3 (delegate)"),
    ("/q4", "Move to Q4 (eliminate)"),
    ("/enrich", "Improve descriptions via Claude"),
    ("/research", "Fetch URLs + summarise findings"),
    ("/daily", "Run daily review"),
    ("/inbox", "Check email inbox"),
    ("/import", "Import unread emails as tasks"),
    ("/email", "Send an email via OutBot"),
    ("/remember", "Save a memory (shared with OutBot)"),
    ("/forget", "Remove a stored memory"),
    ("/telegram", "Send a Telegram message"),
    ("/import-emails", "Import unread emails as tasks"),
    ("/help", "Show available commands"),
]

# Available agents
_AGENTS = [
    ("overseer", "Top-level task orchestration"),
    ("work-tracker", "Create and update work items"),
    ("work-item-enricher", "Enrich vague tasks with AI"),
    ("reminders-importer", "Import from macOS Reminders"),
    ("dashboard-generator", "Generate Eisenhower dashboard"),
    ("overdue-wrangler", "Chase overdue tasks"),
    ("memory-writer", "Document learnings"),
    ("navigator-updater", "Update memory navigator"),
    ("meta-agent", "Audit and improve agents"),
]

# Available skills (top ones)
_SKILLS = [
    ("daily-review", "Import reminders + dashboard"),
    ("frontend-design", "Production-grade frontend"),
    ("docx", "Create/edit Word documents"),
    ("xlsx", "Create/edit spreadsheets"),
    ("pptx", "Create/edit presentations"),
    ("pdf", "Read/manipulate PDFs"),
    ("webapp-testing", "Test web apps with Playwright"),
    ("canvas-design", "Create visual art"),
    ("mcp-builder", "Build MCP servers"),
    ("doc-coauthoring", "Co-author documentation"),
]


class _PaletteItem:
    """A single item in the palette."""

    __slots__ = ("category", "name", "desc", "command")

    def __init__(self, category: str, name: str, desc: str, command: str):
        self.category = category
        self.name = name
        self.desc = desc
        self.command = command


def _build_items(task: dict | None = None) -> list[_PaletteItem]:
    """Build the full palette item list, with suggestions first if task given."""
    items: list[_PaletteItem] = []

    # Contextual suggestions based on current task
    if task:
        suggestions = match_for_task(task)
        for a in suggestions["agents"][:3]:
            items.append(
                _PaletteItem("suggested", a["name"], a["desc"], f"/agent {a['name']}")
            )
        for s in suggestions["skills"][:3]:
            items.append(
                _PaletteItem("suggested", s["name"], s["desc"], f"/skill {s['name']}")
            )

    # Quick actions (edit/note only in focus context)
    if task:
        items.append(_PaletteItem("actions", "edit", "Edit task fields", "edit"))
        items.append(_PaletteItem("actions", "note", "Add a note to task", "note"))

    # Slash commands
    for cmd, desc in _COMMANDS:
        items.append(_PaletteItem("commands", cmd, desc, cmd))

    # Agents
    for name, desc in _AGENTS:
        items.append(_PaletteItem("agents", name, desc, f"/agent {name}"))

    # Skills
    for name, desc in _SKILLS:
        items.append(_PaletteItem("skills", name, desc, f"/skill {name}"))

    return items


class CommandPalette(ModalScreen[str | None]):
    """Full-screen command palette with keyboard navigation."""

    DEFAULT_CSS = """
    CommandPalette {
        align: center middle;
    }
    #palette-box {
        width: 56;
        max-height: 80%;
        background: #1a1a1a;
        border: solid #FF6B35;
        padding: 0;
    }
    #palette-input {
        margin: 1 1 0 1;
        background: #222222;
        border: solid #333333;
    }
    #palette-input:focus {
        border: solid #FF6B35;
        background: #2a2a2a;
    }
    #palette-list {
        height: auto;
        max-height: 40;
        padding: 0 1;
        scrollbar-size: 1 1;
    }
    #palette-hint {
        height: 1;
        padding: 0 1;
        color: #555555;
        background: #111111;
    }
    """

    def __init__(self, task: dict | None = None):
        super().__init__()
        self._task = task
        self._all_items = _build_items(task)
        self._filtered: list[_PaletteItem] = list(self._all_items)
        self._cursor = 0

    def compose(self):
        with Vertical(id="palette-box"):
            yield Input(placeholder="Type to filter...", id="palette-input")
            yield VerticalScroll(
                Static(id="palette-items"),
                id="palette-list",
            )
            yield Static(
                "[dim]↑↓ Navigate  Enter Select  Esc Close[/]",
                id="palette-hint",
            )

    def on_mount(self):
        self._render_list()
        try:
            self.query_one("#palette-input", Input).focus()
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "palette-input":
            return
        query = event.value.lower().strip()
        if not query:
            self._filtered = list(self._all_items)
        else:
            self._filtered = [
                item
                for item in self._all_items
                if query in item.name.lower() or query in item.desc.lower()
            ]
        self._cursor = 0
        self._render_list()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "palette-input":
            return
        # If there's a filter value and no filtered items, treat as raw command
        text = event.value.strip()
        if self._filtered and 0 <= self._cursor < len(self._filtered):
            self.dismiss(self._filtered[self._cursor].command)
        elif text:
            self.dismiss(text)
        else:
            self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        if event.key == "up":
            if self._cursor > 0:
                self._cursor -= 1
                self._render_list()
                self._scroll_to_cursor()
            event.prevent_default()
            event.stop()
        elif event.key == "down":
            if self._cursor < len(self._filtered) - 1:
                self._cursor += 1
                self._render_list()
                self._scroll_to_cursor()
            event.prevent_default()
            event.stop()
        elif event.key == "enter":
            # Handled by on_input_submitted if input focused
            # But also handle if focus is elsewhere
            try:
                inp = self.query_one("#palette-input", Input)
                if not inp.has_focus:
                    if self._filtered and 0 <= self._cursor < len(self._filtered):
                        self.dismiss(self._filtered[self._cursor].command)
            except Exception:
                pass

    def _scroll_to_cursor(self):
        """Ensure the cursor item is visible."""
        try:
            scroll = self.query_one("#palette-list", VerticalScroll)
            # Approximate: each item ~1-2 lines, categories add lines
            # Just scroll to a rough position
            scroll.scroll_to(y=max(0, self._cursor - 5), animate=False)
        except Exception:
            pass

    def _render_list(self) -> None:
        """Render the filtered palette list with cursor highlighting."""
        try:
            panel = self.query_one("#palette-items", Static)
        except Exception:
            return

        if not self._filtered:
            panel.update("[dim]No matches[/]")
            return

        lines: list[str] = []
        current_cat = ""

        for idx, item in enumerate(self._filtered):
            # Category header
            if item.category != current_cat:
                current_cat = item.category
                cat_label = current_cat.upper()
                if lines:
                    lines.append("")
                cat_colours = {
                    "suggested": "#FF6B35",
                    "actions": "#00D4AA",
                    "commands": "#777777",
                    "agents": "#00D4AA",
                    "skills": "#00D4AA",
                }
                colour = cat_colours.get(current_cat, "#777777")
                lines.append(f"[bold {colour}]{cat_label}[/]")

            # Item line
            is_cursor = idx == self._cursor
            if is_cursor:
                marker = "[bold #FF6B35]\u25b8[/]"
                name_fmt = f"[bold #FF6B35]{item.name}[/]"
                desc_fmt = f"[#999999]{item.desc}[/]"
            else:
                marker = " "
                name_fmt = f"[bold]{item.name}[/]"
                desc_fmt = f"[dim]{item.desc}[/]"

            lines.append(f" {marker} {name_fmt}  {desc_fmt}")

        panel.update("\n".join(lines))
