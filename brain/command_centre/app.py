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
from .task_focus import TaskFocusView
from .handlers.voice import VoiceHandler, VOICE_AVAILABLE
from .telegram_bridge import TelegramBridge
from .heartbeat_bridge import HeartbeatBridge
from .brain_logger import log_action


# ---------------------------------------------------------------------------
# Help overlay
# ---------------------------------------------------------------------------

_HELP_TEXT = """\
[bold #FF6B35]COMMAND CENTRE — HOTKEYS[/]
[#333333]\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501[/]

[bold]Navigation[/]
  Arrow keys    Move focus (tiles or fields)
  Enter         Drill into children / open task / edit field
  Space         Toggle select
  Escape        Back one level / clear / quit
  1-9           Jump to tile by position
  \\[  \\]         Page left / right

[bold]Selection[/]
  Space         Toggle select
  a             Select all on page
  n             Deselect all

[bold]Actions[/]
  /             Command palette (commands, agents, skills)
  c             Toggle chat panel (talk to OutBot)
  t             Add to today
  d             Mark done (local + iOS)
  e             Edit task (modal)
  v             Toggle voice mode
  :             Filter (:q1, :overdue, :search)
  ?             This help

[bold]Task Focus View[/]  (when zoomed into a task)
  \u2191 \u2193           Navigate fields + notes/research
  Enter         Edit field / cycle choice
  c             Toggle chat panel
  n             Add a timestamped note
  p             Open/create PRD (Esc saves)
  Escape        Stop editing \u2192 back to grid
  /             Command palette for this task
  t  d          Today / Done

[bold]Voice Mode[/]  (when active)
  Enter         Start / stop recording
  v             Turn voice off
  Escape        Cancel recording

[bold]Quit[/]
  Escape        Back through levels \u2192 double-tap to quit

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

        # View mode: "grid" (tile grid) or "focus" (single-task detail)
        self._view_mode: str = "grid"

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
        """Get the currently focused task (grid or focus view)."""
        if self._view_mode == "focus":
            try:
                fv = self.query_one("#task-focus", TaskFocusView)
                return fv.task
            except Exception:
                return None
        if self.focus_index < len(self.page_tasks):
            return self.page_tasks[self.focus_index]
        return None

    # --- Compose ---

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-area"):
            yield TileGrid(id="tile-grid")
            yield TaskFocusView(id="task-focus")
            yield ContextPanel(id="context-panel")
        yield Static(id="cmd-suggestions")
        yield CommandBarWidget(id="command-bar")
        yield StatusBarWidget(id="status-bar")

    def on_mount(self):
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
            grid = self.query_one("#tile-grid", TileGrid)
            focus_view = self.query_one("#task-focus", TaskFocusView)

            if self._view_mode == "grid":
                grid.styles.display = "block"
                focus_view.styles.display = "none"
                grid.update_tiles(
                    self.page_tasks,
                    self.focus_index,
                    self.selected_ids,
                    self.today_ids,
                    breadcrumb=self._build_breadcrumb(),
                )
            else:
                grid.styles.display = "none"
                focus_view.styles.display = "block"
        except Exception:
            pass

        # Context panel
        panel = self.query_one("#context-panel", ContextPanel)
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

        # --- Focus view keys ---
        if self._view_mode == "focus":
            self._handle_focus_key(key, char, hk)
            return

        # --- Grid view keys ---
        self._handle_grid_key(key, char, hk)

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
        elif char == hk.get("toggle_voice", "v"):
            self._toggle_voice()
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
            self._focus_command_bar(":")

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
            self._focus_command_bar(":")
        elif char == hk.get("chat_toggle", "c"):
            self._toggle_chat()
        elif char == hk.get("toggle_voice", "v"):
            self._toggle_voice()

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

        # 2. Focus view: cancel edit or exit focus
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
            # Route through the command pipeline
            asyncio.create_task(self._run_palette_action(result, task))

        self.push_screen(CommandPalette(task=task), callback=on_dismiss)

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

        # Slash commands or natural language
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
            result = f"[red]Error: {e}[/]"

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
            self._last_response = "[dim]Too short or too quiet — try again[/]"
            self._refresh_all()
            return

        self._last_response = "[dim]Transcribing...[/]"
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
        preview = msg.content[:60] if msg.content else ""
        self.notify(f"TG {name}: {preview}")

        try:
            result = await self.router.route(
                msg.content, set(), None, self.all_tasks, self.today_ids
            )
            if result and self.telegram.available:
                clean = re.sub(r"\[/?[^\]]*\]", "", result)
                if clean.strip():
                    await self.telegram.send(clean.strip())
        except Exception:
            pass

    # --- Heartbeat ---

    async def _init_heartbeat(self):
        try:
            started = await self.heartbeat.start(
                on_notification=self._on_heartbeat_notification
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

    # --- Chat ---

    def _toggle_chat(self):
        """Toggle the context panel between info and chat modes."""
        try:
            panel = self.query_one("#context-panel", ContextPanel)
            panel.toggle_mode()

            if panel.is_chat_mode:
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
            else:
                self.notify("Chat mode OFF")
                self._refresh_all()
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

        # Route through the same pipeline as command bar
        try:
            result = await self.router.route(
                text,
                self.selected_ids,
                focused,
                self.all_tasks,
                self.today_ids,
            )
        except Exception as e:
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
