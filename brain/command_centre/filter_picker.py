"""Filter Picker — navigable list of filter modes.

Triggered by : key. Shows available filters in a keyboard-navigable list
with live filtering and freetext fallback.
"""

from textual import events
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Static


_FILTERS = [
    ("q1", "Q1 — Urgent & Important"),
    ("q2", "Q2 — Important, Not Urgent"),
    ("q3", "Q3 — Urgent, Not Important"),
    ("q4", "Q4 — Not Urgent, Not Important"),
    ("overdue", "Overdue tasks"),
    ("today", "Today shortlist"),
    ("all", "Clear filter (show all)"),
]


class FilterPicker(ModalScreen[str | None]):
    """Full-screen filter picker with keyboard navigation."""

    DEFAULT_CSS = """
    FilterPicker {
        align: center middle;
    }
    #filter-box {
        width: 50;
        max-height: 60%;
        background: #1a1a1a;
        border: solid #FF6B35;
        padding: 0;
    }
    #filter-input {
        margin: 1 1 0 1;
        background: #222222;
        border: solid #333333;
    }
    #filter-input:focus {
        border: solid #FF6B35;
        background: #2a2a2a;
    }
    #filter-list {
        height: auto;
        max-height: 20;
        padding: 0 1;
        scrollbar-size: 1 1;
    }
    #filter-hint {
        height: 1;
        padding: 0 1;
        color: #555555;
        background: #111111;
    }
    """

    def __init__(self):
        super().__init__()
        self._all_filters = list(_FILTERS)
        self._filtered: list[tuple[str, str]] = list(self._all_filters)
        self._cursor = 0

    def compose(self):
        with Vertical(id="filter-box"):
            yield Input(placeholder="Type to filter...", id="filter-input")
            yield VerticalScroll(
                Static(id="filter-items"),
                id="filter-list",
            )
            yield Static(
                "[dim]\u2191\u2193 Navigate  Enter Select  Esc Close[/]",
                id="filter-hint",
            )

    def on_mount(self):
        self._render_list()
        try:
            self.query_one("#filter-input", Input).focus()
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "filter-input":
            return
        query = event.value.lower().strip()
        if not query:
            self._filtered = list(self._all_filters)
        else:
            self._filtered = [
                (name, desc)
                for name, desc in self._all_filters
                if query in name.lower() or query in desc.lower()
            ]
        self._cursor = 0
        self._render_list()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "filter-input":
            return
        text = event.value.strip()
        if self._filtered and 0 <= self._cursor < len(self._filtered):
            self.dismiss(self._filtered[self._cursor][0])
        elif text:
            # Freetext fallback — pass through as search term
            self.dismiss(text)
        else:
            self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        if event.key == "up":
            if self._cursor > 0:
                self._cursor -= 1
                self._render_list()
            event.prevent_default()
            event.stop()
        elif event.key == "down":
            if self._cursor < len(self._filtered) - 1:
                self._cursor += 1
                self._render_list()
            event.prevent_default()
            event.stop()
        elif event.key == "enter":
            event.prevent_default()
            event.stop()
            try:
                inp = self.query_one("#filter-input", Input)
                if not inp.has_focus:
                    if self._filtered and 0 <= self._cursor < len(self._filtered):
                        self.dismiss(self._filtered[self._cursor][0])
            except Exception:
                pass

    def _render_list(self) -> None:
        """Render the filtered list with cursor highlighting."""
        try:
            panel = self.query_one("#filter-items", Static)
        except Exception:
            return

        if not self._filtered:
            panel.update(
                "[dim]No matching filter \u2014 Enter to search tasks[/]"
            )
            return

        lines: list[str] = []
        for idx, (name, desc) in enumerate(self._filtered):
            is_cursor = idx == self._cursor
            if is_cursor:
                marker = "[bold #FF6B35]\u25b8[/]"
                name_fmt = f"[bold #FF6B35]{name}[/]"
                desc_fmt = f"[#999999]{desc}[/]"
            else:
                marker = " "
                name_fmt = f"[bold]{name}[/]"
                desc_fmt = f"[dim]{desc}[/]"
            lines.append(f" {marker} {name_fmt:<12s} {desc_fmt}")

        panel.update("\n".join(lines))
