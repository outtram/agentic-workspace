"""Command Centre — main Textual application."""
import sys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widgets import Input, Static
from textual import events

from . import PROJECT_ROOT
from .config_loader import load_config
from .tile_grid import TileGrid
from .context_panel import ContextPanel
from .command_bar import CommandBarWidget
from .status_bar import StatusBarWidget
from .task_loader import load_tasks, load_today_list, save_today_list
from .router import Router
from .brain_logger import log_action


# ---------------------------------------------------------------------------
# Help overlay
# ---------------------------------------------------------------------------

_HELP_TEXT = """\
[bold #FF6B35]COMMAND CENTRE — HOTKEYS[/]
[#333333]\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501[/]

[bold]Navigation[/]
  Arrow keys    Move focus between tiles
  1-9           Jump to tile by position
  \\[  \\]         Page left / right

[bold]Selection[/]
  Space / Enter Toggle select
  a             Select all on page
  n             Deselect all

[bold]Actions[/]
  t             Add to today
  d             Mark done (local + iOS)
  ?             This help

[bold]Command Bar[/]
  /             Slash commands
  :             Filter (:q1, :overdue, :search)
  Type          Natural language to OutBot

[bold]Slash Commands[/]
  /done         Mark selected tasks done
  /today        Add selected to today
  /remove       Remove from today
  /q1 .. /q4    Move to quadrant
  /enrich       Improve descriptions via Claude
  /daily        Run daily review pipeline
  /help         Show available commands

[bold]Quit[/]
  Escape        Clear selection \u2192 double-tap to quit

[dim]Press any key to close[/]"""


class HelpOverlay(ModalScreen):
    """Full-screen help overlay."""

    DEFAULT_CSS = """
    HelpOverlay {
        align: center middle;
    }
    #help-box {
        width: 52;
        height: auto;
        max-height: 80%;
        background: #1a1a1a;
        border: solid #FF6B35;
        padding: 2;
    }
    """

    def compose(self):
        yield Static(_HELP_TEXT, id="help-box")

    def on_key(self, event: events.Key):
        self.dismiss()


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------


class CommandCentreApp(App):
    """Unified terminal TUI — keyboard-driven task command centre."""

    CSS = """
    Screen {
        background: #1a1a1a;
    }
    #main-area {
        height: 1fr;
    }
    #tile-grid {
        width: 3fr;
    }
    """

    BINDINGS = [
        Binding("escape", "handle_escape", "Quit", priority=True),
    ]

    def __init__(self):
        super().__init__()
        self.all_tasks: list[dict] = []
        self.today_ids: list[str] = []
        self.current_page = 0
        self.focus_index = 0
        self.selected_ids: set[str] = set()
        self._escape_pending = False
        self._hotkeys: dict = {}
        self._panel_mode: str = "detail"  # "detail" | "response"
        self._last_response: str = ""
        self._filter_fn = None
        self._filter_label: str = ""
        self.router = Router()

    @property
    def display_tasks(self) -> list[dict]:
        if self._filter_fn:
            return [t for t in self.all_tasks if self._filter_fn(t)]
        return self.all_tasks

    @property
    def page_tasks(self) -> list[dict]:
        start = self.current_page * 9
        return self.display_tasks[start : start + 9]

    @property
    def total_pages(self) -> int:
        return max(1, (len(self.display_tasks) + 8) // 9)

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-area"):
            yield TileGrid(id="tile-grid")
            yield ContextPanel(id="context-panel")
        yield CommandBarWidget(id="command-bar")
        yield StatusBarWidget(id="status-bar")

    def on_mount(self):
        config = load_config()
        self._hotkeys = config["hotkeys"]
        self.all_tasks = load_tasks()
        self.today_ids = load_today_list()
        self._refresh_all()

    def _refresh_all(self):
        """Update all widgets with current state."""
        grid = self.query_one("#tile-grid", TileGrid)
        grid.update_tiles(
            self.page_tasks, self.focus_index, self.selected_ids, self.today_ids
        )

        panel = self.query_one("#context-panel", ContextPanel)
        focused = (
            self.page_tasks[self.focus_index]
            if self.focus_index < len(self.page_tasks)
            else None
        )
        panel.update_content(
            today_ids=self.today_ids,
            all_tasks=self.all_tasks,
            focused_task=focused if self._panel_mode == "detail" else None,
            response=self._last_response if self._panel_mode == "response" else "",
        )

        status = self.query_one("#status-bar", StatusBarWidget)
        status.update_counts(
            total=len(self.display_tasks),
            today=len(self.today_ids),
            selected=len(self.selected_ids),
            page=self.current_page + 1,
            total_pages=self.total_pages,
            filter_label=self._filter_label,
        )

    # --- Key handling ---

    def on_key(self, event: events.Key):
        # If command bar input is focused, don't handle grid keys
        try:
            cmd_input = self.query_one("#cmd-input", Input)
            if cmd_input.has_focus:
                return
        except Exception:
            pass

        key = event.key
        char = event.character
        hk = self._hotkeys

        # Navigation (always hardcoded — not configurable)
        if key == "up":
            self._focus_up()
        elif key == "down":
            self._focus_down()
        elif key == "left":
            self._focus_left()
        elif key == "right":
            self._focus_right()
        elif key in ("space", "enter"):
            self._toggle_select()
        # Number jump
        elif char and char.isdigit() and char != "0":
            idx = int(char) - 1
            if idx < len(self.page_tasks):
                self.focus_index = idx
                self._escape_pending = False
                self._panel_mode = "detail"
                self._refresh_all()
        # Configurable hotkeys
        elif char == hk.get("add_to_today", "t"):
            self._add_to_today()
        elif char == hk.get("mark_done", "d"):
            self._mark_done()
        elif char == hk.get("select_all", "a"):
            self._select_all()
        elif char == hk.get("deselect_all", "n"):
            self._deselect_all()
        elif char == hk.get("help", "?"):
            self.push_screen(HelpOverlay())
        elif char == hk.get("page_left", "["):
            self._page_left()
        elif char == hk.get("page_right", "]"):
            self._page_right()
        # / or : → focus command bar
        elif char in (hk.get("command_bar", "/"), hk.get("filter_mode", ":")):
            self._focus_command_bar(char)
        # Any other printable char → focus command bar and start typing
        elif char and char.isprintable():
            self._focus_command_bar(char)

    # --- Escape state machine (priority binding) ---

    def action_handle_escape(self):
        # If command bar is focused, blur it
        try:
            cmd_input = self.query_one("#cmd-input", Input)
            if cmd_input.has_focus:
                cmd_input.value = ""
                cmd_input.blur()
                return
        except Exception:
            pass

        if self._filter_fn:
            self._filter_fn = None
            self._filter_label = ""
            self.current_page = 0
            self.focus_index = 0
            self._escape_pending = False
            self._refresh_all()
            self.notify("Filter cleared")
        elif self.selected_ids:
            self.selected_ids.clear()
            self._escape_pending = False
            self._refresh_all()
            self.notify("Selection cleared")
        elif self._panel_mode == "response":
            self._panel_mode = "detail"
            self._last_response = ""
            self._escape_pending = False
            self._refresh_all()
        elif self._escape_pending:
            save_today_list(self.today_ids)
            self.exit()
        else:
            self._escape_pending = True
            self.notify("Press Escape again to quit", severity="warning")
            self.set_timer(2.0, self._reset_escape)

    def _reset_escape(self):
        self._escape_pending = False

    # --- Command bar ---

    def _focus_command_bar(self, initial_char: str = ""):
        """Focus the command bar Input and optionally pre-fill a character."""
        try:
            cmd_input = self.query_one("#cmd-input", Input)
            cmd_input.value = initial_char
            cmd_input.focus()
            cmd_input.cursor_position = len(cmd_input.value)
        except Exception:
            pass

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command bar submission."""
        text = event.value.strip()
        event.input.value = ""
        event.input.blur()

        if not text:
            return

        # Filters handled locally
        if text.startswith(":"):
            self._handle_filter(text[1:].strip())
            return

        # Show thinking state
        self._panel_mode = "response"
        self._last_response = "[dim]Thinking...[/]"
        self._refresh_all()

        # Route command
        focused = (
            self.page_tasks[self.focus_index]
            if self.focus_index < len(self.page_tasks)
            else None
        )

        try:
            result = await self.router.route(
                text, self.selected_ids, focused, self.all_tasks, self.today_ids
            )
        except Exception as e:
            result = f"[red]Error: {e}[/]"

        # Log
        action = "command" if text.startswith("/") else "outbot"
        log_action(action, input_text=text, task_ids=list(self.selected_ids))

        # Update state
        self._last_response = result
        self._panel_mode = "response"
        self.all_tasks = load_tasks()
        self.today_ids = load_today_list()
        self.selected_ids.clear()
        if self.focus_index >= len(self.page_tasks):
            self.focus_index = max(0, len(self.page_tasks) - 1)
        self._refresh_all()

    # --- Filter ---

    def _handle_filter(self, query: str):
        """Apply a filter to the task grid."""
        query = query.lower().strip()

        if query in ("all", "clear", ""):
            self._filter_fn = None
            self._filter_label = ""
            self.notify("Filter cleared")
        elif query == "overdue":
            self._filter_fn = lambda t: t.get("_overdue")
            self._filter_label = "overdue"
            self.notify("Showing overdue tasks")
        elif query in ("q1", "q2", "q3", "q4"):
            q = query
            self._filter_fn = lambda t, _q=q: t.get("eisenhower_quadrant") == _q
            self._filter_label = query.upper()
            self.notify(f"Showing {query.upper()} tasks")
        elif query == "today":
            self._filter_fn = lambda t: t.get("id") in self.today_ids
            self._filter_label = "today"
            self.notify("Showing today tasks")
        else:
            q = query
            self._filter_fn = lambda t, _q=q: (
                _q in t.get("title", "").lower()
                or _q in t.get("_description", "").lower()
            )
            self._filter_label = query
            self.notify(f"Filter: {query}")

        self.current_page = 0
        self.focus_index = 0
        self._refresh_all()

    # --- Navigation ---

    def _focus_left(self):
        col = self.focus_index % 3
        if col > 0 and self.focus_index - 1 < len(self.page_tasks):
            self.focus_index -= 1
            self._escape_pending = False
            self._panel_mode = "detail"
            self._refresh_all()

    def _focus_right(self):
        col = self.focus_index % 3
        if col < 2 and self.focus_index + 1 < len(self.page_tasks):
            self.focus_index += 1
            self._escape_pending = False
            self._panel_mode = "detail"
            self._refresh_all()

    def _focus_up(self):
        if self.focus_index >= 3:
            self.focus_index -= 3
            self._escape_pending = False
            self._panel_mode = "detail"
            self._refresh_all()

    def _focus_down(self):
        new_idx = self.focus_index + 3
        if new_idx < len(self.page_tasks):
            self.focus_index = new_idx
            self._escape_pending = False
            self._panel_mode = "detail"
            self._refresh_all()

    # --- Selection ---

    def _toggle_select(self):
        if self.focus_index >= len(self.page_tasks):
            return
        task = self.page_tasks[self.focus_index]
        tid = task.get("id", "")
        if not tid:
            return
        if tid in self.selected_ids:
            self.selected_ids.discard(tid)
        else:
            self.selected_ids.add(tid)
            log_action("selected", task_ids=[tid])
        self._escape_pending = False
        self._refresh_all()

    def _select_all(self):
        """Select all tasks on current page."""
        for task in self.page_tasks:
            tid = task.get("id", "")
            if tid:
                self.selected_ids.add(tid)
        self._escape_pending = False
        self._refresh_all()
        self.notify(f"Selected {len(self.page_tasks)} tasks")

    def _deselect_all(self):
        """Deselect all tasks."""
        self.selected_ids.clear()
        self._escape_pending = False
        self._refresh_all()
        self.notify("Selection cleared")

    # --- Mark done ---

    def _mark_done(self):
        """Mark focused/selected tasks as done via RemindersManager."""
        ids_to_complete = list(self.selected_ids) if self.selected_ids else []
        if not ids_to_complete and self.focus_index < len(self.page_tasks):
            task = self.page_tasks[self.focus_index]
            tid = task.get("id", "")
            if tid:
                ids_to_complete = [tid]

        if not ids_to_complete:
            return

        sys.path.insert(0, str(PROJECT_ROOT / ".claude"))
        from reminders.core.manager import RemindersManager

        manager = RemindersManager()
        completed = 0
        for tid in ids_to_complete:
            try:
                manager.complete_reminder(tid)
                completed += 1
                if tid in self.today_ids:
                    self.today_ids.remove(tid)
            except Exception:
                pass

        self.all_tasks = [
            t for t in self.all_tasks if t.get("id") not in ids_to_complete
        ]
        self.selected_ids.clear()

        if self.focus_index >= len(self.page_tasks):
            self.focus_index = max(0, len(self.page_tasks) - 1)

        log_action("done", task_ids=ids_to_complete)
        self.notify(f"Completed {completed} task{'s' if completed != 1 else ''}")
        self._refresh_all()

    # --- Today ---

    def _add_to_today(self):
        if self.selected_ids:
            added = 0
            for tid in list(self.selected_ids):
                if tid not in self.today_ids:
                    self.today_ids.append(tid)
                    added += 1
            log_action("added_to_today", task_ids=list(self.selected_ids))
            self.selected_ids.clear()
            if added:
                self.notify(f"Added {added} to today", severity="information")
        elif self.focus_index < len(self.page_tasks):
            task = self.page_tasks[self.focus_index]
            tid = task.get("id", "")
            if tid and tid not in self.today_ids:
                self.today_ids.append(tid)
                log_action("added_to_today", task_ids=[tid])
                self.notify(f"Added {tid} to today", severity="information")
            elif tid and tid in self.today_ids:
                self.today_ids.remove(tid)
                log_action("removed_from_today", task_ids=[tid])
                self.notify(f"Removed {tid} from today", severity="warning")
        self._escape_pending = False
        self._refresh_all()

    # --- Pagination ---

    def _page_left(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.focus_index = 0
            self._escape_pending = False
            self._refresh_all()

    def _page_right(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.focus_index = 0
            self._escape_pending = False
            self._refresh_all()
