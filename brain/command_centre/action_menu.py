"""Action menu modal — quick actions + free text for focused task."""

from textual import events
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from .sanitiser import sanitise
from .skill_matcher import match_for_task
from .task_loader import QUADRANT_COLOURS, QUADRANT_LABELS


# Quick actions — number key → command string
_QUICK_ACTIONS = [
    ("1", "edit", "Edit task fields"),
    ("2", "note", "Add a note to task"),
    ("3", "/enrich", "Enrich description (AI)"),
    ("4", "/research", "Research / fetch URL"),
    ("5", "/q1", "Move to Q1 (urgent+important)"),
    ("6", "/q2", "Move to Q2 (important)"),
    ("7", "/today", "Add to today"),
    ("8", "/done", "Mark done"),
]


class ActionMenuScreen(ModalScreen[str | None]):
    """Modal showing quick actions and free-text input for a task."""

    DEFAULT_CSS = """
    ActionMenuScreen {
        align: center middle;
    }
    #action-box {
        width: 52;
        max-height: 85%;
        background: #1a1a1a;
        border: solid #FF6B35;
        padding: 1 2;
    }
    #action-title {
        margin-bottom: 1;
    }
    #action-list {
        margin-bottom: 0;
    }
    #action-suggestions {
        margin-bottom: 0;
    }
    #action-input {
        margin-top: 1;
        margin-bottom: 0;
    }
    #action-hint {
        color: #555555;
    }
    """

    def __init__(self, task: dict):
        super().__init__()
        self._task_data = task
        self.task_id = task.get("id", "")

    def compose(self):
        title = sanitise(self._task_data.get("title", "Untitled")).replace(
            "[", r"\["
        )
        if len(title) > 40:
            title = title[:37] + "..."
        q = self._task_data.get("eisenhower_quadrant", "q4")
        colour = QUADRANT_COLOURS.get(q, "#3D3D3D")
        label = QUADRANT_LABELS.get(q, "Q4")

        with Vertical(id="action-box"):
            yield Static(
                f"[bold #FF6B35]{self.task_id}[/] [{colour}]{label}[/]\n"
                f"[bold]{title}[/]",
                id="action-title",
            )

            # Quick actions
            lines = "[#333333]" + "\u2501" * 44 + "[/]\n"
            for num, _cmd, desc in _QUICK_ACTIONS:
                lines += f"  [bold #FF6B35]{num}[/]  {desc}\n"
            yield Static(lines, id="action-list")

            # Suggested agents/skills
            suggestions = match_for_task(self._task_data)
            agents = suggestions["agents"]
            skills = suggestions["skills"]

            if agents or skills:
                slines = "[#333333]" + "\u2501" * 44 + "[/]\n"
                slines += "[bold]Suggested[/]\n"
                idx = 9
                if agents:
                    for a in agents[:2]:
                        slines += (
                            f"  [bold #00D4AA]{idx}[/]  "
                            f"[#00D4AA]agent:[/] {a['name']} "
                            f"[dim]— {a['desc']}[/]\n"
                        )
                        idx += 1
                if skills:
                    for s in skills[:2]:
                        slines += (
                            f"  [bold #00D4AA]{idx}[/]  "
                            f"[#00D4AA]skill:[/] {s['name']} "
                            f"[dim]— {s['desc']}[/]\n"
                        )
                        idx += 1
                yield Static(slines, id="action-suggestions")

            # Free text input
            yield Static(
                "[#333333]" + "\u2501" * 44 + "[/]",
            )
            yield Input(
                placeholder='Type a command, note, or question...',
                id="action-input",
            )
            yield Static(
                "[dim]Enter to run  \u00b7  Escape to close[/]",
                id="action-hint",
            )

    def on_mount(self):
        try:
            self.query_one("#action-input", Input).focus()
        except Exception:
            pass

    def on_key(self, event: events.Key) -> None:
        char = event.character

        # Check if input is focused — let it handle its own keys
        try:
            inp = self.query_one("#action-input", Input)
            if inp.has_focus and char and char.isprintable():
                return  # Let input widget handle typing
        except Exception:
            pass

        # Number keys for quick actions
        if char and char.isdigit():
            self._handle_number(char)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle free text submission."""
        text = event.value.strip()
        if text:
            self.dismiss(text)
        else:
            self.dismiss(None)

    def _handle_number(self, num: str) -> None:
        """Handle numbered action selection."""
        # Quick actions 1-7
        for action_num, cmd, _desc in _QUICK_ACTIONS:
            if num == action_num:
                self.dismiss(cmd)
                return

        # Suggested agents/skills 9+
        suggestions = match_for_task(self._task_data)
        all_suggestions = []
        for a in suggestions["agents"][:2]:
            all_suggestions.append(f"/agent {a['name']}")
        for s in suggestions["skills"][:2]:
            all_suggestions.append(f"/skill {s['name']}")

        idx = 9
        for cmd in all_suggestions:
            if num == str(idx):
                self.dismiss(cmd)
                return
            idx += 1
