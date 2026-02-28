"""Command Centre — main Textual application."""
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual import events

from .tile_grid import TileGrid
from .context_panel import ContextPanel
from .command_bar import CommandBarWidget
from .status_bar import StatusBarWidget
from .task_loader import load_tasks, load_today_list, save_today_list


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

    def __init__(self):
        super().__init__()
        self.all_tasks: list[dict] = []
        self.today_ids: list[str] = []
        self.current_page = 0
        self.focus_index = 0
        self.selected_ids: set[str] = set()
        self._escape_pending = False

    @property
    def page_tasks(self) -> list[dict]:
        start = self.current_page * 9
        return self.all_tasks[start : start + 9]

    @property
    def total_pages(self) -> int:
        return max(1, (len(self.all_tasks) + 8) // 9)

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-area"):
            yield TileGrid(id="tile-grid")
            yield ContextPanel(id="context-panel")
        yield CommandBarWidget(id="command-bar")
        yield StatusBarWidget(id="status-bar")

    def on_mount(self):
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
        panel.update_content(self.today_ids, self.all_tasks, focused)

        status = self.query_one("#status-bar", StatusBarWidget)
        status.update_counts(
            total=len(self.all_tasks),
            today=len(self.today_ids),
            selected=len(self.selected_ids),
            page=self.current_page + 1,
            total_pages=self.total_pages,
        )

    # --- Key handling (all in on_key for simplicity) ---

    def on_key(self, event: events.Key):
        key = event.key
        char = event.character

        if key == "escape":
            self._handle_escape()
        elif key == "up":
            self._focus_up()
        elif key == "down":
            self._focus_down()
        elif key == "left":
            self._focus_left()
        elif key == "right":
            self._focus_right()
        elif key in ("space", "enter"):
            self._toggle_select()
        elif char == "t":
            self._add_to_today()
        elif char == "[":
            self._page_left()
        elif char == "]":
            self._page_right()
        elif char and char.isdigit() and char != "0":
            idx = int(char) - 1
            if idx < len(self.page_tasks):
                self.focus_index = idx
                self._escape_pending = False
                self._refresh_all()

    # --- Escape state machine ---

    def _handle_escape(self):
        if self.selected_ids:
            self.selected_ids.clear()
            self._escape_pending = False
            self._refresh_all()
            self.notify("Selection cleared")
        elif self._escape_pending:
            save_today_list(self.today_ids)
            self.exit()
        else:
            self._escape_pending = True
            self.notify("Press Escape again to quit", severity="warning")
            self.set_timer(2.0, self._reset_escape)

    def _reset_escape(self):
        self._escape_pending = False

    # --- Navigation ---

    def _focus_left(self):
        col = self.focus_index % 3
        if col > 0:
            new_idx = self.focus_index - 1
            if new_idx < len(self.page_tasks):
                self.focus_index = new_idx
                self._escape_pending = False
                self._refresh_all()

    def _focus_right(self):
        col = self.focus_index % 3
        if col < 2:
            new_idx = self.focus_index + 1
            if new_idx < len(self.page_tasks):
                self.focus_index = new_idx
                self._escape_pending = False
                self._refresh_all()

    def _focus_up(self):
        if self.focus_index >= 3:
            self.focus_index -= 3
            self._escape_pending = False
            self._refresh_all()

    def _focus_down(self):
        new_idx = self.focus_index + 3
        if new_idx < len(self.page_tasks):
            self.focus_index = new_idx
            self._escape_pending = False
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
        self._escape_pending = False
        self._refresh_all()

    # --- Today ---

    def _add_to_today(self):
        if self.selected_ids:
            added = 0
            for tid in list(self.selected_ids):
                if tid not in self.today_ids:
                    self.today_ids.append(tid)
                    added += 1
            self.selected_ids.clear()
            if added:
                self.notify(f"Added {added} to today", severity="information")
        elif self.focus_index < len(self.page_tasks):
            task = self.page_tasks[self.focus_index]
            tid = task.get("id", "")
            if tid and tid not in self.today_ids:
                self.today_ids.append(tid)
                self.notify(f"Added {tid} to today", severity="information")
            elif tid and tid in self.today_ids:
                self.today_ids.remove(tid)
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
