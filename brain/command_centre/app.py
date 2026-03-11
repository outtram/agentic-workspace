"""Command Centre — main Textual application.

Note: Avoid using _task or _render as attribute names on Widget subclasses —
Textual reserves these internally (asyncio.Task tracking and Visual rendering).
TaskFocusView uses Widget base (not VerticalScroll) to avoid Textual 8.0 render bug.

Navigation model (v2):
  Grid View  → Enter on parent  → Grid shows children (nav stack)
  Grid View  → Enter on leaf    → Task Focus View
  Focus View → Escape           → back to Grid
  Grid View  → Escape           → pop nav stack → clear filter → clear select → quit

Key changes from v1:
  - Enter = drill down (into children or focus view).  Space = toggle select.
  - / opens the Command Palette (navigable modal with agents/skills/commands).
  - : still opens the command bar for filters.
  - AI progress shows a step-by-step log with elapsed time.
"""

import asyncio
import re
import sys
import time
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widgets import Input, Static, TextArea
from textual import events

from . import PROJECT_ROOT
from .config_loader import load_config
from .tile_grid import TileGrid
from .context_panel import ContextPanel
from .command_bar import CommandBarWidget
from .status_bar import StatusBarWidget
from .task_loader import load_tasks, load_today_list, save_today_list
from .router import Router
from .task_editor import TaskEditScreen
from .predictions import generate_predictions
from .command_palette import CommandPalette
from .filter_picker import FilterPicker
from .task_focus import TaskFocusView
from .diagram_grid import DiagramGrid, list_diagrams, DIAGRAMS_DIR
from .handlers.voice import VoiceHandler, VOICE_AVAILABLE
from .telegram_bridge import TelegramBridge
from .heartbeat_bridge import HeartbeatBridge
from .brain_logger import log_action
from .cc_logger import logger as cc_log
from .stream_list import StreamList
from .bump import (
    bump_top, bump_back, mark_seen, snooze,
    undo_last, stream_sort_key, check_snoozed,
)
from .bump_persist import save_stream_state
from .task_loader import find_task_file


# ---------------------------------------------------------------------------
# Help overlay
# ---------------------------------------------------------------------------

_HELP_TEXT = """\
[bold #FF6B35]COMMAND CENTRE — HOTKEYS[/]
[#333333]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]

[bold]Navigation[/]
  Arrow keys    Move focus between tiles
  Enter         Drill down — parent task → show children; leaf task → open Focus View
  Space         Toggle select on focused tile
  1-9           Jump to tile by position
  [ / ]         Page left / right

[bold]Selection[/]
  a             Select all on page
  n             Deselect all

[bold]Actions[/]
  /             Command Palette — all commands, agents, and skills in a filterable list
  c             Toggle chat panel (talk to OutBot)
  t             Add selected (or focused) to today
  d             Mark done (local + iOS)
  e             Edit focused task (modal)
  v             Toggle voice mode
  :             Filter Picker — select from quadrants, overdue, today, or search
  ?             Show help overlay
  Escape        Back one level → clear filter → clear selection → double-tap to quit

[bold]Stream View[/]
[bold]  Navigation[/]
  ↑ / ↓         Navigate items
  PgUp / PgDn   Jump 10 items
  Home / End    Jump to top / bottom
  Enter         Open item (switches to focus view)
[bold]  Actions[/]
  t             Bump to top (marks as NEW)
  b             Bump to back (sinks to bottom)
  s             Snooze (1h / tomorrow / next week)
  d             Mark done
  z             Undo last bump
  v             Cycle view (Stream → Grid → Diagram)
  c             Toggle chat (split layout)
  /             Commands
  :             Filter
  ?             Help

[bold]Task Focus View[/]  (when zoomed into a task)
  ↑ / ↓         Navigate between fields
  Enter         Edit field (text input) or cycle choice (quadrant/priority/status)
  Escape        Stop editing → back to field list → back to grid
  /             Command Palette for this task (agents, skills, commands)
  c             Toggle chat panel
  n             Add a timestamped note
  p             Open/create PRD (editable, Esc saves, includes research)
  t             Add to today
  d             Mark done
  Space         Toggle select

[bold]Diagram View[/]  (/diagram)
  Arrow keys    Move focus between nodes
  Enter         Drill into node's children (if any)
  1-9           Jump to node by position
  /             Command Palette
  c             Toggle chat panel
  ?             Show help overlay
  Escape        Zoom out one layer → exit diagram at root

[bold]Filter Picker[/]  (: key)
  ↑ / ↓         Navigate between filters
  Enter         Apply selected filter
  Type          Filter list or freetext search
  Escape        Close picker

[bold]Voice Mode[/]  (when active)
  Enter         Start / stop recording
  v             Turn voice off
  Escape        Cancel current recording

[bold]Quit[/]
  Escape        Back through levels → double-tap to quit

[dim]Press any key to close[/]"""


class HelpOverlay(ModalScreen):
    """Full-screen help overlay."""

    DEFAULT_CSS = """
    HelpOverlay {
        align: center middle;
    }
    #help-box {
        width: 56;
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
# Diagram picker
# ---------------------------------------------------------------------------


class DiagramPicker(ModalScreen):
    """Simple modal to pick a diagram file from .claude/diagrams/."""

    DEFAULT_CSS = """
    DiagramPicker {
        align: center middle;
    }
    #dpick-box {
        width: 48;
        max-height: 60%;
        background: #1a1a1a;
        border: solid #FF6B35;
        padding: 1 2;
    }
    """

    def __init__(self, diagrams: list):
        super().__init__()
        self._diagrams = diagrams
        self._cursor = 0

    def compose(self):
        yield Static(id="dpick-box")

    def on_mount(self):
        self._refresh_list()

    def on_key(self, event: events.Key):
        if event.key == "up" and self._cursor > 0:
            self._cursor -= 1
            self._refresh_list()
            event.stop()
        elif event.key == "down" and self._cursor < len(self._diagrams) - 1:
            self._cursor += 1
            self._refresh_list()
            event.stop()
        elif event.key == "enter":
            self.dismiss(self._diagrams[self._cursor])
            event.stop()

    def _refresh_list(self):
        lines = ["[bold #FF6B35]SELECT DIAGRAM[/]", ""]
        for i, d in enumerate(self._diagrams):
            marker = "[bold #FF6B35]\u25b8[/]" if i == self._cursor else " "
            name = d.stem.replace("-", " ").title()
            if i == self._cursor:
                lines.append(f"  {marker} [bold #FF6B35]{name}[/]")
            else:
                lines.append(f"  {marker} {name}")
        lines.append("")
        lines.append("[dim]\u2191\u2193 Navigate  Enter Select  Esc Cancel[/]")
        try:
            self.query_one("#dpick-box", Static).update("\n".join(lines))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------


class CommandCentreApp(App):
    """Unified terminal TUI — keyboard-driven task command centre."""

    AUTO_FOCUS = None

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
    #diagram-grid {
        width: 3fr;
        display: none;
    }
    #stream-list {
        width: 3fr;
        display: none;
    }
    #stream-list.chat-active {
        width: 1fr;
        opacity: 0.3;
    }
    #cmd-suggestions {
        height: auto;
        max-height: 14;
        background: #222222;
        border-top: solid #FF6B35;
        padding: 0 1;
        display: none;
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

        # View mode: "stream", "grid", "focus", or "diagram"
        self._view_mode: str = "stream"
        self._diagram_path: Path | None = None

        # Stream bump state
        self._undo_stack: list[dict] = []
        self._notification_timer = None
        self._snooze_pending = False

        # Navigation stack — list of parent task IDs we've drilled into
        self._nav_stack: list[str] = []

        # Panel mode
        self._panel_mode: str = "detail"  # "detail" | "response" | "predictions"
        self._last_response: str = ""

        # Filtering
        self._filter_fn = None
        self._filter_label: str = ""

        # AI progress tracking
        self._progress_log: list[tuple[float, str]] = []
        self._progress_start: float | None = None
        self._progress_timer = None

        # Subsystems
        self.router = Router()
        self.voice = VoiceHandler()
        self.telegram = TelegramBridge()
        self.heartbeat = HeartbeatBridge()
        self._predictions: list[dict] = []
        self._predictions_pending = False

    # --- Properties ---

    @property
    def display_tasks(self) -> list[dict]:
        """Return tasks filtered by nav stack and any active filter."""
        tasks = self.all_tasks

        # If we've drilled into a parent, show only its children
        if self._nav_stack:
            parent_id = self._nav_stack[-1]
            # Find children: tasks whose parent matches, or whose ID is in
            # the parent task's children list
            parent_task = None
            for t in self.all_tasks:
                if t.get("id") == parent_id:
                    parent_task = t
                    break

            child_ids = set()
            if parent_task:
                child_ids = set(parent_task.get("children", []))

            tasks = [
                t
                for t in self.all_tasks
                if t.get("parent") == parent_id or t.get("id") in child_ids
            ]

        if self._filter_fn:
            tasks = [t for t in tasks if self._filter_fn(t)]

        return tasks

    @property
    def page_tasks(self) -> list[dict]:
        start = self.current_page * 9
        return self.display_tasks[start : start + 9]

    @property
    def total_pages(self) -> int:
        return max(1, (len(self.display_tasks) + 8) // 9)

    @property
    def _focused_task(self) -> dict | None:
        """Get the currently focused task (grid, stream, or focus view)."""
        if self._view_mode == "focus":
            try:
                fv = self.query_one("#task-focus", TaskFocusView)
                return fv.task
            except Exception:
                return None
        if self._view_mode == "stream":
            return self._focused_stream_task
        if self.focus_index < len(self.page_tasks):
            return self.page_tasks[self.focus_index]
        return None

    # --- Compose ---

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-area"):
            yield StreamList(id="stream-list")
            yield TileGrid(id="tile-grid")
            yield TaskFocusView(id="task-focus")
            yield DiagramGrid(id="diagram-grid")
            yield ContextPanel(id="context-panel")
        yield Static(id="cmd-suggestions")
        yield CommandBarWidget(id="command-bar")
        yield StatusBarWidget(id="status-bar")

    def on_mount(self):
        cc_log.info("=== CC started ===  tasks=%d", len(load_tasks()))
        config = load_config()
        self._hotkeys = config["hotkeys"]
        self.all_tasks = load_tasks()
        self.today_ids = load_today_list()

        # Generate predictions on launch
        self._predictions = generate_predictions(self.all_tasks, self.today_ids)
        if self._predictions:
            self._predictions_pending = True
            self._panel_mode = "predictions"

        self._refresh_all()

        # Start Telegram bridge in background
        asyncio.create_task(self._init_telegram())

        # Start heartbeat bridge in background
        asyncio.create_task(self._init_heartbeat())

    # --- Refresh ---

    def _refresh_all(self):
        """Update all widgets with current state."""
        # Toggle visibility based on view mode
        try:
            stream = self.query_one("#stream-list", StreamList)
            grid = self.query_one("#tile-grid", TileGrid)
            focus_view = self.query_one("#task-focus", TaskFocusView)
            diagram_grid = self.query_one("#diagram-grid", DiagramGrid)

            if self._view_mode == "stream":
                stream.styles.display = "block"
                grid.styles.display = "none"
                focus_view.styles.display = "none"
                diagram_grid.styles.display = "none"

                sorted_tasks = sorted(self.all_tasks, key=stream_sort_key)
                visible = [
                    t for t in sorted_tasks
                    if t.get("stream_state") != "snoozed"
                ]
                stream.update_items(visible, self.focus_index)
            elif self._view_mode == "grid":
                stream.styles.display = "none"
                grid.styles.display = "block"
                focus_view.styles.display = "none"
                diagram_grid.styles.display = "none"
                grid.update_tiles(
                    self.page_tasks,
                    self.focus_index,
                    self.selected_ids,
                    self.today_ids,
                    breadcrumb=self._build_breadcrumb(),
                )
            elif self._view_mode == "focus":
                stream.styles.display = "none"
                grid.styles.display = "none"
                focus_view.styles.display = "block"
                diagram_grid.styles.display = "none"
            elif self._view_mode == "diagram":
                stream.styles.display = "none"
                grid.styles.display = "none"
                focus_view.styles.display = "none"
                diagram_grid.styles.display = "block"
        except Exception:
            pass

        # Context panel
        panel = self.query_one("#context-panel", ContextPanel)

        if self._view_mode == "diagram":
            try:
                dg = self.query_one("#diagram-grid", DiagramGrid)
                panel.update_diagram_node(dg.focused_node, self.all_tasks)
            except Exception:
                pass
        else:
            focused = self._focused_task
            response = ""
            if self._panel_mode == "response":
                response = self._build_progress_display()
            elif self._panel_mode == "predictions" and self._predictions_pending:
                response = self._render_predictions()

            panel.update_content(
                today_ids=self.today_ids,
                all_tasks=self.all_tasks,
                focused_task=focused if self._panel_mode == "detail" else None,
                response=response,
            )

        # Status bar
        status = self.query_one("#status-bar", StatusBarWidget)
        if self._view_mode == "diagram":
            try:
                dg = self.query_one("#diagram-grid", DiagramGrid)
                status.update_counts(
                    view_mode="diagram",
                    diagram_title=dg.diagram_title,
                    diagram_depth=dg.layer_depth,
                    diagram_node_count=len(dg.visible_nodes),
                )
            except Exception:
                pass
        elif self._view_mode == "stream":
            new_count = sum(1 for t in self.all_tasks if t.get("stream_state") == "new")
            back_count = sum(1 for t in self.all_tasks if t.get("stream_state") == "back")
            snoozed_count = sum(1 for t in self.all_tasks if t.get("stream_state") == "snoozed")
            status.update_counts(
                total=len(self.all_tasks),
                view_mode="stream",
                stream_new=new_count,
                stream_back=back_count,
                stream_snoozed=snoozed_count,
                telegram_status=self.telegram.status_label,
                heartbeat_status=self.heartbeat.status_label,
            )
        else:
            overdue = sum(1 for t in self.all_tasks if t.get("_overdue"))
            status.update_counts(
                total=len(self.display_tasks),
                today=len(self.today_ids),
                selected=len(self.selected_ids),
                page=self.current_page + 1,
                total_pages=self.total_pages,
                filter_label=self._filter_label,
                voice_active=self.voice.active,
                voice_recording=self.voice.recording,
                overdue=overdue,
                telegram_status=self.telegram.status_label,
                heartbeat_status=self.heartbeat.status_label,
                view_mode=self._view_mode,
                nav_depth=len(self._nav_stack),
            )

        # Command bar label
        self._update_command_bar_label()

    def _update_command_bar_label(self):
        """Update command bar hint text based on mode."""
        try:
            cmd_label = self.query_one("#cmd-label", Static)
            cmd_input = self.query_one("#cmd-input", Input)
            if self.voice.active:
                cmd_label.update("[bold #FF6B35]\u266a[/] ")
                if self.voice.recording:
                    cmd_input.placeholder = "Recording... press Enter to stop"
                else:
                    cmd_input.placeholder = "VOICE ON  Enter=record  v=stop voice"
            elif self._view_mode == "focus":
                cmd_label.update("[bold #FF6B35]\u25c9[/] ")
                cmd_input.placeholder = (
                    "/ commands  : filter  or type to talk to OutBot"
                )
            else:
                cmd_label.update("\u2318 ")
                cmd_input.placeholder = (
                    "/ commands  : filter  or type to talk to OutBot"
                )
        except Exception:
            pass

    def _build_breadcrumb(self) -> str:
        """Build a breadcrumb string for navigation depth."""
        if not self._nav_stack:
            return ""
        parts = []
        task_map = {t["id"]: t for t in self.all_tasks if "id" in t}
        for tid in self._nav_stack:
            t = task_map.get(tid)
            if t:
                name = t.get("title", tid)
                if len(name) > 20:
                    name = name[:17] + "..."
                parts.append(f"{tid}: {name}")
            else:
                parts.append(tid)
        return " \u203a ".join(parts)

    # --- Key handling ---

    def on_key(self, event: events.Key):
        # Don't handle keys when a modal is active — let the modal handle them
        if len(self.screen_stack) > 1:
            return

        # If the focus-edit-input or focus-edit-area is active, let them handle keys
        if self._view_mode == "focus":
            try:
                fv = self.query_one("#task-focus", TaskFocusView)
                if fv.is_editing:
                    # Let the editor widgets handle their own keys
                    # Only intercept Escape (handled by priority binding)
                    return
            except Exception:
                pass

        # If command bar or chat input is focused, don't handle grid/focus keys
        try:
            cmd_input = self.query_one("#cmd-input", Input)
            if cmd_input.has_focus:
                return
        except Exception:
            pass
        try:
            chat_input = self.query_one("#chat-input", Input)
            if chat_input.has_focus:
                return
        except Exception:
            pass

        key = event.key
        char = event.character
        hk = self._hotkeys

        # Prediction acceptance
        if self._predictions_pending and self._panel_mode == "predictions":
            if char == "y":
                self._accept_predictions()
                return
            elif char == "n":
                self._dismiss_predictions()
                return

        # Voice mode — Enter starts/stops recording
        if self.voice.active and key == "enter":
            self._voice_enter()
            return

        # --- Stream view keys ---
        if self._view_mode == "stream":
            self._handle_stream_key(key, char, hk)
            return

        # --- Focus view keys ---
        if self._view_mode == "focus":
            self._handle_focus_key(key, char, hk)
            return

        # --- Diagram view keys ---
        if self._view_mode == "diagram":
            self._handle_diagram_key(key, char, hk)
            return

        # --- Grid view keys ---
        self._handle_grid_key(key, char, hk)

    def _handle_stream_key(self, key: str, char: str | None, hk: dict):
        """Handle keys in stream mode."""
        # Handle pending snooze choice
        if self._snooze_pending and char in ("1", "2", "3"):
            self._stream_handle_snooze_choice(char)
            return

        if key == "up":
            if self.focus_index > 0:
                self.focus_index -= 1
                self._panel_mode = "detail"
                self._refresh_all()
        elif key == "down":
            try:
                stream = self.query_one("#stream-list", StreamList)
                max_idx = len(stream.tasks) - 1
                if self.focus_index < max_idx:
                    self.focus_index += 1
                    self._panel_mode = "detail"
                    self._refresh_all()
            except Exception:
                pass
        elif key == "pageup":
            self.focus_index = max(0, self.focus_index - 10)
            self._refresh_all()
        elif key == "pagedown":
            try:
                stream = self.query_one("#stream-list", StreamList)
                max_idx = max(0, len(stream.tasks) - 1)
                self.focus_index = min(max_idx, self.focus_index + 10)
                self._refresh_all()
            except Exception:
                pass
        elif key == "home":
            self.focus_index = 0
            self._refresh_all()
        elif key == "end":
            try:
                stream = self.query_one("#stream-list", StreamList)
                self.focus_index = max(0, len(stream.tasks) - 1)
                self._refresh_all()
            except Exception:
                pass
        elif key == "enter":
            self._stream_open_item()
        elif char == "t":
            self._stream_bump_top()
        elif char == "b":
            self._stream_bump_back()
        elif char == "s":
            self._stream_snooze()
        elif char == "z":
            self._stream_undo()
        elif char == hk.get("mark_done", "d"):
            self._mark_done()
        elif char == hk.get("cycle_view", "v"):
            self._cycle_view()
        elif char == hk.get("command_bar", "/"):
            self._open_command_palette()
        elif char == hk.get("chat_toggle", "c"):
            self._toggle_chat()
        elif char == hk.get("filter_mode", ":"):
            self._open_filter_picker()
        elif char == hk.get("help", "?"):
            self.push_screen(HelpOverlay())

    def _handle_grid_key(self, key: str, char: str | None, hk: dict):
        """Handle keys in grid mode."""
        # Navigation
        if key == "up":
            self._focus_up()
        elif key == "down":
            self._focus_down()
        elif key == "left":
            self._focus_left()
        elif key == "right":
            self._focus_right()
        elif key == "enter":
            self._drill_down()
        elif key == "space":
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
        elif char == hk.get("cycle_view", "v"):
            self._cycle_view()
        elif char == hk.get("add_to_today", "t"):
            self._add_to_today()
        elif char == hk.get("mark_done", "d"):
            self._mark_done()
        elif char == hk.get("edit_task", "e"):
            self._edit_task()
        elif char == hk.get("action_menu", "x"):
            self._open_command_palette()
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
        elif char == hk.get("command_bar", "/"):
            self._open_command_palette()
        elif char == hk.get("chat_toggle", "c"):
            self._toggle_chat()
        elif char == hk.get("filter_mode", ":"):
            self._open_filter_picker()

    def _handle_focus_key(self, key: str, char: str | None, hk: dict):
        """Handle keys in focus view."""
        try:
            fv = self.query_one("#task-focus", TaskFocusView)
        except Exception:
            return

        if key == "up":
            fv.move_cursor(-1)
        elif key == "down":
            fv.move_cursor(1)
        elif key == "enter":
            fv.start_edit()
        elif key == "space":
            # Toggle select on the focused task
            task = fv.task
            if task:
                tid = task.get("id", "")
                if tid:
                    if tid in self.selected_ids:
                        self.selected_ids.discard(tid)
                    else:
                        self.selected_ids.add(tid)
                        log_action("selected", task_ids=[tid])
                    self._refresh_all()
        elif char == "n":
            fv.start_add_note()
        elif char == "p":
            fv.open_or_create_prd()
        elif char == hk.get("add_to_today", "t"):
            self._add_to_today()
        elif char == hk.get("mark_done", "d"):
            self._mark_done()
        elif char == hk.get("command_bar", "/"):
            self._open_command_palette()
        elif char == hk.get("action_menu", "x"):
            self._open_command_palette()
        elif char == hk.get("help", "?"):
            self.push_screen(HelpOverlay())
        elif char == hk.get("filter_mode", ":"):
            self._open_filter_picker()
        elif char == hk.get("chat_toggle", "c"):
            self._toggle_chat()
        elif char == hk.get("cycle_view", "v"):
            self._cycle_view()

    def _handle_diagram_key(self, key: str, char: str | None, hk: dict):
        """Handle keys in diagram mode."""
        try:
            dg = self.query_one("#diagram-grid", DiagramGrid)
        except Exception:
            return

        cols = dg.grid_cols
        node_count = len(dg.visible_nodes)

        if key == "up":
            new_idx = dg.focus_index - cols
            if new_idx >= 0:
                dg.focus_index = new_idx
                self._refresh_all()
        elif key == "down":
            new_idx = dg.focus_index + cols
            if new_idx < node_count:
                dg.focus_index = new_idx
                self._refresh_all()
        elif key == "left":
            if dg.focus_index % cols > 0 and dg.focus_index > 0:
                dg.focus_index -= 1
                self._refresh_all()
        elif key == "right":
            if dg.focus_index % cols < cols - 1 and dg.focus_index + 1 < node_count:
                dg.focus_index += 1
                self._refresh_all()
        elif key == "enter":
            dg.drill_in()
            self._escape_pending = False
            self._refresh_all()
        elif char and char.isdigit() and char != "0":
            idx = int(char) - 1
            if 0 <= idx < node_count:
                dg.focus_index = idx
                self._refresh_all()
        elif char == hk.get("cycle_view", "v"):
            self._cycle_view()
        elif char == hk.get("command_bar", "/"):
            self._open_command_palette()
        elif char == hk.get("help", "?"):
            self.push_screen(HelpOverlay())
        elif char == hk.get("chat_toggle", "c"):
            self._toggle_chat()

    # --- Escape state machine ---

    def action_handle_escape(self):
        # 1. Dismiss modals
        if len(self.screen_stack) > 1:
            top = self.screen_stack[-1]
            if isinstance(top, ModalScreen):
                if isinstance(top, TaskEditScreen):
                    top.dismiss(False)
                else:
                    top.dismiss(None)
                return

        # 2. Diagram mode: zoom out or exit to grid
        if self._view_mode == "diagram":
            try:
                dg = self.query_one("#diagram-grid", DiagramGrid)
                if dg.zoom_out():
                    self._refresh_all()
                    return
            except Exception:
                pass
            self._exit_diagram()
            return

        # 3. Focus view: cancel edit or exit focus
        if self._view_mode == "focus":
            try:
                fv = self.query_one("#task-focus", TaskFocusView)
                if fv.is_editing:
                    # Textarea needs special handling — save on Escape
                    try:
                        area = fv.query_one("#focus-edit-area", TextArea)
                        if area.styles.display != "none":
                            fv.handle_textarea_escape()
                            return
                    except Exception:
                        pass
                    fv.cancel_edit()
                    return
            except Exception:
                pass
            # Not editing — exit focus view
            self._exit_focus()
            return

        # 3. Command bar focused — blur + clear
        try:
            cmd_input = self.query_one("#cmd-input", Input)
            if cmd_input.has_focus:
                cmd_input.value = ""
                cmd_input.blur()
                self._hide_suggestions()
                return
        except Exception:
            pass

        # 3b. Chat input focused — blur + exit chat mode
        try:
            chat_input = self.query_one("#chat-input", Input)
            if chat_input.has_focus:
                chat_input.value = ""
                chat_input.blur()
                return
        except Exception:
            pass

        # 3c. Chat mode active — switch back to info mode
        try:
            panel = self.query_one("#context-panel", ContextPanel)
            if panel.is_chat_mode:
                panel.toggle_mode()
                self.notify("Chat mode OFF")
                self._refresh_all()
                return
        except Exception:
            pass

        # 4. Voice recording
        if self.voice.recording:
            self.voice.stop_recording()
            self.notify("Recording cancelled")
            self._refresh_all()
            return

        # 5. Predictions panel
        if self._predictions_pending and self._panel_mode == "predictions":
            self._dismiss_predictions()
            return

        # 6. Nav stack — go back up one level
        if self._nav_stack:
            self._nav_stack.pop()
            self.current_page = 0
            self.focus_index = 0
            self._escape_pending = False
            self._panel_mode = "detail"
            self._refresh_all()
            parent_name = ""
            if self._nav_stack:
                parent_name = self._nav_stack[-1]
            self.notify(
                f"Back to {parent_name}" if parent_name else "Back to all tasks"
            )
            return

        # 7. Filter → Selection → Response → Quit cascade
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
            self._progress_log.clear()
            self._progress_start = None
            self._escape_pending = False
            self._refresh_all()
        elif self._escape_pending:
            save_today_list(self.today_ids)
            if self.telegram.available:
                asyncio.create_task(self.telegram.stop())
            if self.heartbeat.running:
                asyncio.create_task(self.heartbeat.stop())
            self.exit()
        else:
            self._escape_pending = True
            self.notify("Press Escape again to quit", severity="warning")
            self.set_timer(2.0, self._reset_escape)

    def _reset_escape(self):
        self._escape_pending = False

    # --- Drill-down (Enter in grid) ---

    def _drill_down(self):
        """Enter on a tile: drill into children or open focus view."""
        if self.focus_index >= len(self.page_tasks):
            return
        task = self.page_tasks[self.focus_index]
        if not task.get("id"):
            return

        children = task.get("children", [])

        if children:
            # Has children — drill into them (push nav stack)
            self._nav_stack.append(task["id"])
            self.current_page = 0
            self.focus_index = 0
            self._escape_pending = False
            self._panel_mode = "detail"
            self._refresh_all()
            self.notify(f"Showing subtasks of {task['id']}")
        else:
            # Leaf task — open focus view
            self._enter_focus(task)

    def _enter_focus(self, task: dict):
        """Switch to focus view for a specific task."""
        self._view_mode = "focus"
        self._escape_pending = False
        self._panel_mode = "detail"

        try:
            fv = self.query_one("#task-focus", TaskFocusView)
            fv.show_task(task)
        except Exception:
            pass

        log_action("focus_entered", task_ids=[task.get("id", "")])
        self._refresh_all()

    def _exit_focus(self):
        """Switch back to grid view from focus view."""
        self._view_mode = "grid"
        self._escape_pending = False

        # Reload tasks in case focus view made edits
        self.all_tasks = load_tasks()
        self.today_ids = load_today_list()

        if self.focus_index >= len(self.page_tasks):
            self.focus_index = max(0, len(self.page_tasks) - 1)

        try:
            fv = self.query_one("#task-focus", TaskFocusView)
            fv.clear()
        except Exception:
            pass

        self._refresh_all()
        self.notify("Back to grid")

    # --- View cycling ---

    def _cycle_view(self):
        """Cycle view: stream -> grid -> diagram -> stream."""
        if self._view_mode == "stream":
            self._view_mode = "grid"
            self.focus_index = 0
            self.current_page = 0
        elif self._view_mode == "grid":
            if list_diagrams():
                self._view_mode = "diagram"
                self._enter_diagram()
            else:
                self._view_mode = "stream"
                self.focus_index = 0
        elif self._view_mode == "diagram":
            self._view_mode = "stream"
            self.focus_index = 0
        self._refresh_all()

    # --- Stream bump actions ---

    def _stream_bump_top(self):
        """Bump focused stream item to top."""
        task = self._focused_stream_task
        if not task:
            return
        bump_top(task, self._undo_stack)
        self._persist_stream_state(task)
        self.focus_index = 0
        self._refresh_all()

    def _stream_bump_back(self):
        """Bump focused stream item to back."""
        task = self._focused_stream_task
        if not task:
            return
        bump_back(task, self._undo_stack)
        self._persist_stream_state(task)
        self._refresh_all()

    def _stream_snooze(self):
        """Show snooze picker for focused item."""
        self.notify(
            "Snooze: [bold]1[/]=1h  [bold]2[/]=tomorrow  [bold]3[/]=next week",
            timeout=5,
        )
        self._snooze_pending = True

    def _stream_handle_snooze_choice(self, choice: str):
        """Handle snooze duration choice."""
        task = self._focused_stream_task
        if not task:
            return
        hours_map = {"1": 1, "2": 24, "3": 168}
        hours = hours_map.get(choice)
        if hours:
            snooze(task, hours=hours, undo_stack=self._undo_stack)
            self._persist_stream_state(task)
            self._refresh_all()
        self._snooze_pending = False

    def _stream_undo(self):
        """Undo last bump action."""
        if not self._undo_stack:
            self.notify("Nothing to undo")
            return
        entry = self._undo_stack[-1]
        tid = entry["task_id"]
        for task in self.all_tasks:
            if task.get("id") == tid:
                undo_last(task, self._undo_stack)
                self._persist_stream_state(task)
                self._refresh_all()
                return
        self.notify(f"Task {tid} not found")

    def _stream_open_item(self):
        """Open focused stream item in focus view, mark as seen."""
        task = self._focused_stream_task
        if not task:
            return
        mark_seen(task)
        self._persist_stream_state(task)
        self._enter_focus(task)

    @property
    def _focused_stream_task(self) -> dict | None:
        """Get the currently focused task in stream view."""
        try:
            stream = self.query_one("#stream-list", StreamList)
            tasks = stream.tasks
            if self.focus_index < len(tasks):
                return tasks[self.focus_index]
        except Exception:
            pass
        return None

    def _persist_stream_state(self, task: dict):
        """Save stream state to task's markdown file."""
        path = find_task_file(task.get("id", ""))
        if path:
            save_stream_state(
                path,
                stream_state=task.get("stream_state", "new"),
                last_touched=task.get("last_touched", ""),
                snoozed_until=task.get("snoozed_until"),
            )

    def _show_stream_notification(self, message: str):
        """Show a notification in the stream widget that auto-hides after 3s."""
        if self._view_mode != "stream":
            return
        try:
            stream = self.query_one("#stream-list", StreamList)
            stream.show_notification(message)
            if self._notification_timer is not None:
                self._notification_timer.stop()
            self._notification_timer = self.set_timer(
                3.0, self._hide_stream_notification
            )
        except Exception:
            pass

    def _hide_stream_notification(self):
        """Hide the stream notification bar."""
        try:
            stream = self.query_one("#stream-list", StreamList)
            stream.hide_notification()
        except Exception:
            pass
        self._notification_timer = None

    # --- Diagram mode switching ---

    def _enter_diagram(self, path=None):
        """Switch to diagram mode. If no path, show picker or auto-load."""
        from pathlib import Path

        diagrams = list_diagrams()
        if not diagrams:
            self.notify("No diagrams in .claude/diagrams/", severity="warning")
            return

        if path and Path(path).exists():
            self._view_mode = "diagram"
            self._escape_pending = False
            try:
                dg = self.query_one("#diagram-grid", DiagramGrid)
                dg.load(Path(path))
            except Exception:
                pass
            self._refresh_all()
            self.notify(f"Diagram: {Path(path).stem}")
            return

        # One diagram — load directly
        if len(diagrams) == 1:
            self._view_mode = "diagram"
            self._escape_pending = False
            try:
                dg = self.query_one("#diagram-grid", DiagramGrid)
                dg.load(diagrams[0])
            except Exception:
                pass
            self._refresh_all()
            self.notify(f"Diagram: {diagrams[0].stem}")
            return

        # Multiple — show picker
        def on_pick(result):
            if result is not None:
                self._view_mode = "diagram"
                self._escape_pending = False
                try:
                    dg = self.query_one("#diagram-grid", DiagramGrid)
                    dg.load(result)
                except Exception:
                    pass
                self._refresh_all()
                self.notify(f"Diagram: {result.stem}")

        self.push_screen(DiagramPicker(diagrams), callback=on_pick)

    def _exit_diagram(self):
        """Switch back to task grid from diagram mode."""
        self._view_mode = "grid"
        self._escape_pending = False
        self._refresh_all()
        self.notify("Back to tasks")

    # --- Command palette ---

    def _open_command_palette(self):
        """Open the command palette (replaces / suggestions and x action menu)."""
        task = self._focused_task

        def on_dismiss(result: str | None) -> None:
            if result is None:
                return
            if result == "edit":
                self._edit_task()
                return
            if result == "note":
                if task:
                    self._add_note_to_task(task)
                return
            # Diagram/tasks mode switching (handled locally)
            if result.lower().startswith("/diagram"):
                args = result[8:].strip()
                if args:
                    self._enter_diagram(DIAGRAMS_DIR / f"{args}.json")
                else:
                    self._enter_diagram()
                return
            if result.lower() == "/tasks":
                self._exit_diagram()
                return
            # Route through the command pipeline
            asyncio.create_task(self._run_palette_action(result, task))

        self.push_screen(CommandPalette(task=task), callback=on_dismiss)

    def _open_filter_picker(self):
        """Open the filter picker modal (replaces : command bar prefill)."""

        def on_dismiss(result: str | None) -> None:
            if result is not None:
                self._handle_filter(result)

        self.push_screen(FilterPicker(), callback=on_dismiss)

    async def _run_palette_action(self, command: str, task: dict | None):
        """Execute a command from the palette."""
        tid = task.get("id", "") if task else ""

        # Ensure task is targeted
        if tid and tid not in self.selected_ids:
            self.selected_ids.add(tid)

        # Start progress tracking
        self._start_progress(f"Running: {command}")

        try:
            result = await self.router.route(
                command,
                self.selected_ids,
                task,
                self.all_tasks,
                self.today_ids,
                progress=self._update_progress,
            )
        except Exception as e:
            result = f"[red]Error: {e}[/]"

        # Finish progress tracking
        self._finish_progress(result)

        log_action("command", input_text=command, task_ids=[tid] if tid else [])

        # Reload state
        self.all_tasks = load_tasks()
        self.today_ids = load_today_list()
        self.selected_ids.clear()
        if self.focus_index >= len(self.page_tasks):
            self.focus_index = max(0, len(self.page_tasks) - 1)

        # If in focus mode, refresh the focus view with updated task
        if self._view_mode == "focus" and tid:
            for t in self.all_tasks:
                if t.get("id") == tid:
                    try:
                        fv = self.query_one("#task-focus", TaskFocusView)
                        fv.show_task(t)
                    except Exception:
                        pass
                    break

        self._refresh_all()

        # Speak if voice active
        if self.voice.active and VOICE_AVAILABLE and result:
            clean = re.sub(r"\[/?[^\]]*\]", "", result)
            if clean.strip():
                asyncio.get_running_loop().run_in_executor(
                    None, self._speak_text, clean.strip()
                )

    # --- Command bar (for : filter and OutBot) ---

    def _focus_command_bar(self, initial_char: str = ""):
        """Focus the command bar for filter mode or OutBot chat."""
        try:
            cmd_input = self.query_one("#cmd-input", Input)
            cmd_input.value = initial_char
            cmd_input.focus()
            cmd_input.cursor_position = len(cmd_input.value)
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes — suggestions for command bar."""
        if event.input.id == "cmd-input":
            text = event.value
            if text.startswith("/"):
                self._update_suggestions(text)
            else:
                self._hide_suggestions()

    def _update_suggestions(self, text: str) -> None:
        """Show filtered slash command suggestions (lightweight fallback)."""
        try:
            panel = self.query_one("#cmd-suggestions", Static)
        except Exception:
            return

        from .command_palette import _COMMANDS

        query = text.lower()
        matches = [(cmd, desc) for cmd, desc in _COMMANDS if cmd.startswith(query)]

        if not matches:
            self._hide_suggestions()
            return

        lines = []
        for cmd, desc in matches[:8]:
            lines.append(f"  [bold #FF6B35]{cmd}[/]  [dim]{desc}[/]")

        panel.update("\n".join(lines))
        panel.styles.display = "block"

    def _hide_suggestions(self) -> None:
        try:
            self.query_one("#cmd-suggestions", Static).styles.display = "none"
        except Exception:
            pass

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Input submissions from command bar or focus editor."""
        # Focus view inline editor
        if event.input.id == "focus-edit-input":
            try:
                fv = self.query_one("#task-focus", TaskFocusView)
                fv.handle_input_submitted(event.value)
            except Exception:
                pass
            return

        # Chat input
        if event.input.id == "chat-input":
            text = event.value.strip()
            event.input.value = ""
            if text:
                asyncio.create_task(self._handle_chat_message(text))
            return

        # Command bar
        if event.input.id != "cmd-input":
            return

        self._hide_suggestions()
        text = event.value.strip()
        event.input.value = ""
        event.input.blur()

        if not text:
            return

        # Filters handled locally
        if text.startswith(":"):
            self._handle_filter(text[1:].strip())
            return

        # Diagram/tasks mode switching (handled locally)
        if text.lower().startswith("/diagram"):
            args = text[8:].strip()
            if args:
                self._enter_diagram(DIAGRAMS_DIR / f"{args}.json")
            else:
                self._enter_diagram()
            return
        if text.lower() == "/tasks":
            self._exit_diagram()
            return

        # Slash commands or natural language
        cc_log.info("CMD  %s  selected=%s", text, list(self.selected_ids))
        self._start_progress(f"Running: {text}")

        focused = self._focused_task

        try:
            result = await self.router.route(
                text,
                self.selected_ids,
                focused,
                self.all_tasks,
                self.today_ids,
                progress=self._update_progress,
            )
        except Exception as e:
            cc_log.exception("CMD ERROR  %s", text)
            result = f"[red]Error: {e}[/]"

        cc_log.info("CMD OK  %s  len=%d", text, len(result))
        self._finish_progress(result)

        action = "command" if text.startswith("/") else "outbot"
        log_action(action, input_text=text, task_ids=list(self.selected_ids))

        self.all_tasks = load_tasks()
        self.today_ids = load_today_list()
        self.selected_ids.clear()
        if self.focus_index >= len(self.page_tasks):
            self.focus_index = max(0, len(self.page_tasks) - 1)
        self._refresh_all()

        if self.voice.active and VOICE_AVAILABLE and result:
            clean = re.sub(r"\[/?[^\]]*\]", "", result)
            if clean.strip():
                asyncio.get_running_loop().run_in_executor(
                    None, self._speak_text, clean.strip()
                )

    # --- AI Progress Tracking ---

    def _start_progress(self, label: str):
        """Begin tracking an AI operation with progress log."""
        self._progress_log.clear()
        self._progress_start = time.time()
        self._progress_log.append((time.time(), label))
        self._panel_mode = "response"
        self._last_response = ""
        self._refresh_all()

        # Start a timer to update elapsed time every second
        self._cancel_progress_timer()
        self._progress_timer = self.set_interval(1.0, self._tick_progress)

    def _cancel_progress_timer(self):
        """Stop the progress update timer."""
        if self._progress_timer is not None:
            self._progress_timer.stop()
            self._progress_timer = None

    def _tick_progress(self):
        """Called every second to update the elapsed time display."""
        if self._progress_start is not None:
            self._refresh_all()

    async def _update_progress(self, msg: str) -> None:
        """Progress callback — accumulates messages in the progress log."""
        clean_msg = re.sub(r"\[/?[^\]]*\]", "", msg).strip()
        if clean_msg:
            self._progress_log.append((time.time(), clean_msg))
        self._panel_mode = "response"
        self._refresh_all()

    def _finish_progress(self, result: str):
        """End progress tracking and show final result."""
        self._cancel_progress_timer()
        elapsed = 0.0
        if self._progress_start:
            elapsed = time.time() - self._progress_start
        self._progress_start = None

        # Build final display: log + result
        if elapsed > 0:
            self._progress_log.append(
                (time.time(), f"Completed in {elapsed:.1f}s")
            )

        self._last_response = result
        self._panel_mode = "response"
        self._refresh_all()

    def _build_progress_display(self) -> str:
        """Build the progress panel content with log and elapsed time."""
        lines: list[str] = []

        # Show progress log entries
        if self._progress_log:
            lines.append("[bold #FF6B35]PROGRESS[/]")
            lines.append("[#333333]" + "\u2501" * 24 + "[/]")

            for ts, msg in self._progress_log:
                # Show relative time from start
                if self._progress_start:
                    rel = ts - self._progress_start
                    lines.append(f"[dim]{rel:5.1f}s[/]  {msg}")
                else:
                    lines.append(f"  {msg}")

            # Show elapsed time if still running
            if self._progress_start is not None:
                elapsed = time.time() - self._progress_start
                lines.append("")
                lines.append(f"[bold #FF6B35]\u23f1 {elapsed:.0f}s elapsed[/]")

            lines.append("")

        # Show final response if available
        if self._last_response:
            lines.append("[bold #FF6B35]RESULT[/]")
            lines.append("[#333333]" + "\u2501" * 24 + "[/]")
            lines.append(self._last_response)

        return "\n".join(lines) if lines else "[dim]Thinking...[/]"

    # --- Filter ---

    def _handle_filter(self, query: str):
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

    # --- Grid navigation ---

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
        for task in self.page_tasks:
            tid = task.get("id", "")
            if tid:
                self.selected_ids.add(tid)
        self._escape_pending = False
        self._refresh_all()
        self.notify(f"Selected {len(self.page_tasks)} tasks")

    def _deselect_all(self):
        self.selected_ids.clear()
        self._escape_pending = False
        self._refresh_all()
        self.notify("Selection cleared")

    # --- Mark done ---

    def _mark_done(self):
        ids_to_complete = list(self.selected_ids) if self.selected_ids else []

        # In focus mode, target the focused task
        if not ids_to_complete:
            task = self._focused_task
            if task:
                tid = task.get("id", "")
                if tid:
                    ids_to_complete = [tid]

        if not ids_to_complete:
            return

        claude_dir = str(PROJECT_ROOT / ".claude")
        if claude_dir not in sys.path:
            sys.path.insert(0, claude_dir)

        try:
            from reminders.core.manager import RemindersManager
        except ImportError:
            self.notify("RemindersManager not available", severity="error")
            return

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

        # If in focus view and task was completed, exit focus
        if self._view_mode == "focus":
            self._exit_focus()

        if self.focus_index >= len(self.page_tasks):
            self.focus_index = max(0, len(self.page_tasks) - 1)

        save_today_list(self.today_ids)
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
        else:
            task = self._focused_task
            if task:
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
        save_today_list(self.today_ids)
        self._refresh_all()

    # --- Voice ---

    def _toggle_voice(self):
        if not VOICE_AVAILABLE:
            self.notify("Voice unavailable (sounddevice/whisper not installed)")
            return
        active = self.voice.toggle()
        self._escape_pending = False
        self._refresh_all()
        self.notify(f"Voice {'ON' if active else 'OFF'}")

    def _voice_enter(self):
        if self.voice.recording:
            self._voice_stop()
        else:
            self._voice_start()

    def _voice_start(self):
        if self.voice.start_recording():
            self._panel_mode = "response"
            self._last_response = (
                "[bold #FF6B35]Recording...[/]\n[dim]Press Enter to stop[/]"
            )
            self._refresh_all()
        else:
            self.notify("Failed to start recording — check microphone")

    def _voice_stop(self):
        audio = self.voice.stop_recording()
        if audio is None:
            self._progress_log.clear()
            self._progress_start = None
            self._last_response = "[dim]Too short or too quiet — try again[/]"
            self._panel_mode = "response"
            self._refresh_all()
            return

        self._progress_log.clear()
        self._progress_start = None
        self._last_response = "[dim]Transcribing...[/]"
        self._panel_mode = "response"
        self._refresh_all()
        asyncio.create_task(self._voice_pipeline(audio))

    async def _voice_pipeline(self, audio):
        from brain.voice import transcribe, speak

        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, transcribe, audio)
        if not text:
            self._last_response = "[dim]Couldn't understand that — try again[/]"
            self._refresh_all()
            return

        self._start_progress(f"Voice: {text}")

        focused = self._focused_task

        try:
            result = await self.router.route(
                text,
                self.selected_ids,
                focused,
                self.all_tasks,
                self.today_ids,
                progress=self._update_progress,
            )
        except Exception as e:
            result = f"[red]Error: {e}[/]"

        self._finish_progress(f"[dim]You said:[/] {text}\n\n{result}")

        log_action("voice", input_text=text, task_ids=list(self.selected_ids))

        self.all_tasks = load_tasks()
        self.today_ids = load_today_list()
        self.selected_ids.clear()
        if self.focus_index >= len(self.page_tasks):
            self.focus_index = max(0, len(self.page_tasks) - 1)
        self._refresh_all()

        clean = re.sub(r"\[/?[^\]]*\]", "", result)
        if clean.strip():
            await loop.run_in_executor(None, speak, clean.strip())

    @staticmethod
    def _speak_text(text: str):
        from brain.voice import speak

        speak(text)

    # --- Predictions ---

    def _render_predictions(self) -> str:
        lines = "[bold #FF6B35]BRAIN SUGGESTS[/]\n"
        lines += "[#333333]" + "\u2501" * 24 + "[/]\n\n"
        for pred in self._predictions:
            title = pred.get("title", pred["id"])
            if len(title) > 30:
                title = title[:27] + "..."
            lines += f"  [bold]{pred['id']}[/] {title}\n"
        lines += "\n[bold]Accept? [#00D4AA]y[/] = add to today  [#FF6B35]n[/] = dismiss[/]"
        return lines

    def _accept_predictions(self):
        added = 0
        for pred in self._predictions:
            tid = pred["id"]
            if tid not in self.today_ids:
                self.today_ids.append(tid)
                added += 1
        self._predictions_pending = False
        save_today_list(self.today_ids)
        self._panel_mode = "detail"
        self._refresh_all()
        self.notify(f"Added {added} suggested tasks to today")

    def _dismiss_predictions(self):
        self._predictions_pending = False
        self._panel_mode = "detail"
        self._refresh_all()
        self.notify("Predictions dismissed")

    # --- Edit (legacy modal — kept for backward compat) ---

    def _edit_task(self):
        task = self._focused_task
        if not task or not task.get("id"):
            return

        def on_dismiss(result: bool | None) -> None:
            if result:
                self.all_tasks = load_tasks()
                self.today_ids = load_today_list()
                if self.focus_index >= len(self.page_tasks):
                    self.focus_index = max(0, len(self.page_tasks) - 1)
                # Update focus view if active
                if self._view_mode == "focus":
                    tid = task.get("id", "")
                    for t in self.all_tasks:
                        if t.get("id") == tid:
                            try:
                                fv = self.query_one("#task-focus", TaskFocusView)
                                fv.show_task(t)
                            except Exception:
                                pass
                            break
                self._refresh_all()
                self.notify("Task updated")

        self.push_screen(TaskEditScreen(task), callback=on_dismiss)

    # --- Note ---

    def _add_note_to_task(self, task: dict):
        from .note_modal import NoteModal

        task_id = task.get("id", "")
        if not task_id:
            return

        def on_note(result: str | None) -> None:
            if not result:
                return
            from .task_loader import find_task_file

            task_file = find_task_file(task_id)
            if not task_file:
                self.notify("Task file not found", severity="error")
                return
            content = task_file.read_text()
            timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
            note_block = f"\n\n## Note ({timestamp})\n\n{result}\n"
            task_file.write_text(content.rstrip() + note_block)
            self.all_tasks = load_tasks()
            self._refresh_all()
            self.notify("Note added")

        self.push_screen(NoteModal(task_id), callback=on_note)

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

    # --- Telegram ---

    async def _init_telegram(self):
        try:
            started = await self.telegram.start(
                on_message=self._on_telegram_message
            )
            if started:
                self.router._telegram_bridge = self.telegram
                self._refresh_all()
        except Exception:
            pass

    async def _on_telegram_message(self, msg):
        name = msg.sender_name or "Unknown"
        chat_id = getattr(msg, "chat_jid", "")
        preview = msg.content[:60] if msg.content else ""
        self.notify(f"TG {name}: {preview}")

        # Auto-save chat_id to .env if missing
        if chat_id and not self.telegram._config.telegram_chat_id:
            self.notify(f"TG: saving chat_id {chat_id}", severity="information")
            self.telegram._config.telegram_chat_id = chat_id
            try:
                env_path = Path(__file__).resolve().parents[1] / ".env"
                text = env_path.read_text()
                text = text.replace(
                    "OUTBOT_TELEGRAM_CHAT_ID=",
                    f"OUTBOT_TELEGRAM_CHAT_ID={chat_id}",
                )
                env_path.write_text(text)
            except Exception as e:
                self.notify(f"TG: .env write failed: {e}", severity="warning")

        # Show in chat panel
        try:
            panel = self.query_one("#context-panel", ContextPanel)
            panel.add_chat_message("user", f"[TG] {msg.content}")
        except Exception:
            pass

        try:
            result = await self.router.route(
                msg.content, set(), None, self.all_tasks, self.today_ids
            )
            if result and self.telegram.available:
                clean = re.sub(r"\[/?[^\]]*\]", "", result)
                if clean.strip():
                    await self.telegram.send(clean.strip())
                    try:
                        panel = self.query_one("#context-panel", ContextPanel)
                        panel.add_chat_message("assistant", clean.strip())
                    except Exception:
                        pass
        except Exception as e:
            self.notify(f"TG error: {type(e).__name__}: {e}", severity="error")

    # --- Heartbeat ---

    async def _init_heartbeat(self):
        try:
            started = await self.heartbeat.start(
                on_notification=self._on_heartbeat_notification,
                on_new_items=self._on_new_items_arrived,
            )
            if started:
                self._refresh_all()
        except Exception:
            pass

    async def _on_heartbeat_notification(self, message: str):
        """Handle a heartbeat notification — show toast and update panel."""
        self.notify(f"\u2764 {message[:80]}")

        # If chat mode is active, inject as system message
        try:
            panel = self.query_one("#context-panel", ContextPanel)
            if panel.is_chat_mode:
                panel.add_system_message(message)
                return
        except Exception:
            pass

        # Otherwise show in the response panel
        self._last_response = f"[bold #FF6B35]\u2764 HEARTBEAT[/]\n{message}"
        self._panel_mode = "response"
        self._refresh_all()

    async def _on_new_items_arrived(self, message: str):
        """Called by heartbeat when new emails/reminders found."""
        self.all_tasks = load_tasks()
        self._show_stream_notification(message)
        self._refresh_all()

    # --- Chat ---

    def _toggle_chat(self):
        """Toggle chat mode — in stream view, use split layout."""
        try:
            panel = self.query_one("#context-panel", ContextPanel)
            if panel.is_chat_mode:
                panel.toggle_mode()
                if self._view_mode == "stream":
                    try:
                        stream = self.query_one("#stream-list", StreamList)
                        stream.remove_class("chat-active")
                    except Exception:
                        pass
                    panel.remove_class("chat-hero")
                self.notify("Chat mode OFF")
                self._refresh_all()
            else:
                panel.toggle_mode()
                if self._view_mode == "stream":
                    try:
                        stream = self.query_one("#stream-list", StreamList)
                        stream.add_class("chat-active")
                    except Exception:
                        pass
                    panel.add_class("chat-hero")
                # Set task context from selected + focused tasks
                context_tasks = []
                context_ids = set()
                if self.selected_ids:
                    for t in self.all_tasks:
                        tid = t.get("id")
                        if tid in self.selected_ids:
                            context_tasks.append(t)
                            context_ids.add(tid)
                focused = self._focused_task
                if focused and focused.get("id") not in context_ids:
                    context_tasks.append(focused)
                panel.set_task_context(context_tasks)
                self.notify("Chat mode ON  (c to switch back)")
        except Exception:
            pass

    async def _handle_chat_message(self, text: str):
        """Process a message from the chat input."""
        try:
            panel = self.query_one("#context-panel", ContextPanel)
        except Exception:
            return

        # Add user message to chat
        panel.add_chat_message("user", text)

        # Build task context from selected + focused tasks
        context_tasks = []
        context_ids = set()
        if self.selected_ids:
            for t in self.all_tasks:
                tid = t.get("id")
                if tid in self.selected_ids:
                    context_tasks.append(t)
                    context_ids.add(tid)
        focused = self._focused_task
        if focused and focused.get("id") not in context_ids:
            context_tasks.append(focused)
        panel.set_task_context(context_tasks)

        # Progress callback that shows steps as system messages in chat
        async def _chat_progress(msg: str) -> None:
            clean_msg = re.sub(r"\[/?[^\]]*\]", "", msg).strip()
            if clean_msg:
                cc_log.debug("CHAT STEP  %s", clean_msg)
                panel.add_chat_message("system", clean_msg)

        cc_log.info("CHAT  %s", text)
        panel.add_chat_message("system", "Thinking...")

        # Route through the same pipeline as command bar
        try:
            result = await self.router.route(
                text,
                self.selected_ids,
                focused,
                self.all_tasks,
                self.today_ids,
                progress=_chat_progress,
            )
        except Exception as e:
            cc_log.exception("CHAT ERROR  %s", text)
            result = f"Error: {e}"

        # Strip Rich markup for chat display
        clean = re.sub(r"\[/?[^\]]*\]", "", result)
        panel.add_chat_message("assistant", clean.strip() if clean.strip() else result)

        log_action("chat", input_text=text, task_ids=list(self.selected_ids))

        # Reload state (in case command changed tasks)
        self.all_tasks = load_tasks()
        self.today_ids = load_today_list()

        # Speak if voice active
        if self.voice.active and VOICE_AVAILABLE and clean.strip():
            asyncio.get_running_loop().run_in_executor(
                None, self._speak_text, clean.strip()
            )
