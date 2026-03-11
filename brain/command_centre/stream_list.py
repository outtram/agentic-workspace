"""Stream view widget — inbox-style scrollable list sorted by recency."""
from datetime import datetime

from textual.containers import Container, VerticalScroll
from textual.widgets import Static

from .sanitiser import sanitise

# Source label colours
_SOURCE_COLOURS = {
    "email": "#FF6B35",
    "reminder": "#d4aa00",
    "task": "#00D4AA",
}


def _relative_time(iso_str: str) -> str:
    """Convert ISO timestamp to relative time string like '2m ago'."""
    try:
        dt = datetime.fromisoformat(iso_str)
        delta = datetime.now() - dt
        secs = int(delta.total_seconds())
        if secs < 0:
            return "now"
        if secs < 60:
            return f"{secs}s ago"
        mins = secs // 60
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        if days < 7:
            return f"{days}d ago"
        weeks = days // 7
        return f"{weeks}w ago"
    except (ValueError, TypeError):
        return ""


def render_stream_row(task: dict, focused: bool = False) -> str:
    """Render a single stream row as Rich markup."""
    state = task.get("stream_state", "new")
    title = sanitise(task.get("title", "Untitled")).replace("[", r"\[")
    if len(title) > 60:
        title = title[:57] + "..."

    source = task.get("source", "task")
    source_colour = _SOURCE_COLOURS.get(source, "#888888")
    last_touched = task.get("last_touched", "")
    rel_time = _relative_time(last_touched)

    if focused:
        icon = "[#FF6B35]▸[/]"
    elif state == "new":
        icon = "[#00D4AA]●[/]"
    elif state == "seen":
        icon = "[#666666]○[/]"
    else:  # back
        icon = "[#444444]◌[/]"

    badge = ""
    if not focused:
        if state == "new":
            badge = "[#00D4AA on #00D4AA20] NEW [/] "
        elif state == "back":
            badge = "[#666666 on #333333] BACK [/] "

    # Title brightness by state
    if state == "new" or focused:
        title_markup = f"[bold]{title}[/]"
    elif state == "seen":
        title_markup = f"[#999999]{title}[/]"
    else:  # back
        title_markup = f"[#666666]{title}[/]"

    source_markup = f"[{source_colour}]{source}[/]"
    time_markup = f"[dim]{rel_time}[/]"

    return f" {icon}  {badge}{title_markup}  {source_markup}  {time_markup}"


class StreamList(Container):
    """Inbox-style scrollable stream of tasks."""

    DEFAULT_CSS = """
    StreamList {
        padding: 0;
        overflow: hidden;
    }
    #stream-notification {
        height: auto;
        max-height: 2;
        display: none;
        padding: 0 2;
        background: #1a2e1a;
    }
    #stream-scroll {
        height: 1fr;
        scrollbar-size: 1 1;
    }
    .stream-row {
        height: 1;
        padding: 0 1;
    }
    .stream-row.focused {
        background: #2a2000;
    }
    .stream-row.state-back {
        opacity: 0.5;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tasks: list[dict] = []
        self._focus_index: int = 0

    def compose(self):
        yield Static(id="stream-notification")
        with VerticalScroll(id="stream-scroll"):
            for i in range(100):
                yield Static(id=f"srow-{i}", classes="stream-row")

    def update_items(
        self,
        tasks: list[dict],
        focus_index: int,
    ):
        """Re-render all stream rows."""
        self._tasks = tasks
        self._focus_index = focus_index

        for i in range(100):
            try:
                row = self.query_one(f"#srow-{i}", Static)
            except Exception:
                break

            row.remove_class("focused", "state-new", "state-seen", "state-back")

            if i < len(tasks):
                task = tasks[i]
                is_focused = i == focus_index
                row.update(render_stream_row(task, focused=is_focused))
                row.styles.display = "block"

                if is_focused:
                    row.add_class("focused")

                state = task.get("stream_state", "new")
                row.add_class(f"state-{state}")
            else:
                row.update("")
                row.styles.display = "none"

        self._scroll_to_focus(focus_index)

    def _scroll_to_focus(self, index: int):
        """Scroll the VerticalScroll to keep focused row visible."""
        try:
            scroll = self.query_one("#stream-scroll", VerticalScroll)
            row = self.query_one(f"#srow-{index}", Static)
            scroll.scroll_visible(row, animate=False)
        except Exception:
            pass

    def show_notification(self, message: str):
        """Show a notification bar at the top (auto-hidden by app timer)."""
        try:
            notif = self.query_one("#stream-notification", Static)
            notif.update(f"[#00D4AA]{message}[/]")
            notif.styles.display = "block"
        except Exception:
            pass

    def hide_notification(self):
        """Hide the notification bar."""
        try:
            notif = self.query_one("#stream-notification", Static)
            notif.styles.display = "none"
        except Exception:
            pass

    @property
    def focus_index(self) -> int:
        return self._focus_index

    @property
    def tasks(self) -> list[dict]:
        return self._tasks
