#!/usr/bin/env python3
"""Interactive terminal task picker — keyboard-driven Eisenhower triage.

Launch:  python3 .claude/scripts/task-picker.py

Keys:
  Left / h   — skip task
  Right / l  — add to "today" list
  Up / k     — previous task
  Down / j   — next task
  Enter      — drill into subtasks (if parent)
  Backspace  — zoom back to parent view
  Tab        — toggle today sidebar
  Escape / q — save & quit
"""

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
_TASK_DIR = _PROJECT_ROOT / ".claude" / "work" / "tasks"
_DASHBOARD_DIR = _PROJECT_ROOT / ".claude" / "dashboards"
_TODAY_FILE = _DASHBOARD_DIR / "today.yml"

# ---------------------------------------------------------------------------
# Task loading
# ---------------------------------------------------------------------------

QUADRANT_WEIGHT = {"q1": 4, "q2": 3, "q3": 2, "q4": 1}
QUADRANT_LABEL = {
    "q1": ("Q1 \u00b7 DO FIRST", "red"),
    "q2": ("Q2 \u00b7 SCHEDULE", "yellow"),
    "q3": ("Q3 \u00b7 DELEGATE", "cyan"),
    "q4": ("Q4 \u00b7 ELIMINATE", "dim white"),
}


def _parse_task_file(path: Path) -> Optional[dict]:
    """Read a task markdown file with YAML frontmatter."""
    text = path.read_text()
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict):
        return None

    # Extract description from body (first paragraph after # heading)
    body = parts[2].strip()
    desc_lines = []
    in_desc = False
    for line in body.split("\n"):
        if line.startswith("## Description"):
            in_desc = True
            continue
        if in_desc:
            if line.startswith("##"):
                break
            desc_lines.append(line)
    meta["_description"] = "\n".join(desc_lines).strip()
    meta["_file"] = path.name
    return meta


def load_tasks() -> list[dict]:
    """Read, weight, and sort all active tasks."""
    tasks = []
    today = date.today()

    for f in sorted(_TASK_DIR.glob("OUT-*.md")):
        t = _parse_task_file(f)
        if t is None or t.get("status") not in ("todo", "open", "draft"):
            continue

        # Calculate weight
        q = t.get("eisenhower_quadrant", "q4")
        weight = QUADRANT_WEIGHT.get(q, 1)

        due = t.get("due_date")
        if due:
            try:
                if isinstance(due, str) and due:
                    due_date = datetime.fromisoformat(due).date()
                elif isinstance(due, date):
                    due_date = due
                else:
                    due_date = None
            except (ValueError, TypeError):
                due_date = None

            if due_date:
                days_until = (due_date - today).days
                if days_until < 0:
                    weight += 3  # overdue bonus
                    t["_overdue"] = True
                elif days_until == 0:
                    weight += 2  # due today
                    t["_due_today"] = True
                elif days_until <= 3:
                    weight += 1  # due soon
                t["_due_date"] = due_date

        t["_weight"] = weight
        tasks.append(t)

    tasks.sort(key=lambda t: t["_weight"], reverse=True)
    return tasks


def filter_tasks_for_view(all_tasks: list[dict], parent_id: Optional[str]) -> list[dict]:
    """Filter tasks for a hierarchy view level.

    parent_id=None  → root view: tasks with no parent + parent tasks
    parent_id='OUT-350' → children of that parent
    """
    if parent_id is None:
        return [t for t in all_tasks if not t.get("parent")]
    return [t for t in all_tasks if t.get("parent") == parent_id]


def load_today_list() -> list[str]:
    """Load previously saved today list."""
    if _TODAY_FILE.exists():
        try:
            data = yaml.safe_load(_TODAY_FILE.read_text())
            if isinstance(data, dict):
                return data.get("tasks", [])
        except yaml.YAMLError:
            pass
    return []


def save_today_list(task_ids: list[str]):
    """Save today list to YAML."""
    _DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "date": date.today().isoformat(),
        "updated": datetime.now().isoformat(),
        "tasks": task_ids,
    }
    _TODAY_FILE.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


# ---------------------------------------------------------------------------
# Textual TUI
# ---------------------------------------------------------------------------

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Static
    from textual.containers import Vertical
    from textual.binding import Binding
    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False


if HAS_TEXTUAL:
    class TaskCard(Static):
        """Renders a single task as a styled card."""

        def __init__(self, task: dict, index: int, total: int, **kwargs):
            super().__init__(**kwargs)
            self._task_data = task
            self._index = index
            self._total = total

        def render(self):
            t = self._task_data
            out_id = t.get("id", "???")
            # Escape Rich markup in user content
            title = t.get("title", "Untitled").replace("[", r"\[")
            q = t.get("eisenhower_quadrant", "q4")
            label, colour = QUADRANT_LABEL.get(q, ("Q4", "dim white"))
            priority = t.get("priority", "low")
            raw_desc = t.get("_description", "")
            desc = raw_desc[:200].replace("[", r"\[")
            if len(raw_desc) > 200:
                desc += "..."

            # Status badges
            badges = f"[bold {colour}]{label}[/]"
            if t.get("_overdue"):
                badges += "    [bold red]OVERDUE[/]"
            elif t.get("_due_today"):
                badges += "    [bold yellow]DUE TODAY[/]"

            # Hierarchy badges
            children = t.get("children", [])
            if children:
                badges += f"    [bold magenta]\[{len(children)} subtask{'s' if len(children) != 1 else ''}][/]"
            parent_id = t.get("parent")
            if parent_id:
                badges += f"    [dim]parent: {parent_id}[/]"
            prd_id = t.get("prd")
            if prd_id:
                badges += f"    [bold blue]PRD: {prd_id}[/]"

            # Due date display
            due_str = ""
            if "_due_date" in t:
                due_str = f"  \u00b7  due: {t['_due_date'].strftime('%d %b')}"

            # Build as Rich markup string
            lines = f"\n  {badges}\n\n"
            lines += f"  [bold]{title}[/]\n\n"
            lines += f"  [dim]{out_id}{due_str}  \u00b7  {priority}[/]\n\n"
            if desc:
                words = desc.split()
                line = "  "
                for w in words:
                    if len(line) + len(w) + 1 > 55:
                        lines += line + "\n"
                        line = "  " + w
                    else:
                        line += (" " if len(line) > 2 else "") + w
                if line.strip():
                    lines += line + "\n"
            lines += "\n"

            return lines

    class TodaySidebar(Static):
        """Shows tasks marked for today."""

        def __init__(self, today_ids: list[str], all_tasks: list[dict], **kwargs):
            super().__init__(**kwargs)
            self.today_ids = today_ids
            self.all_tasks = all_tasks

        def render(self):
            lines = "  [bold green]TODAY[/]\n\n"
            if not self.today_ids:
                lines += "  [dim](none yet)[/]\n"
                lines += "  [dim]Press \u25b6 to add tasks[/]\n"
            else:
                task_map = {t["id"]: t for t in self.all_tasks if "id" in t}
                for tid in self.today_ids:
                    t = task_map.get(tid)
                    if t:
                        q = t.get("eisenhower_quadrant", "q4")
                        _, colour = QUADRANT_LABEL.get(q, ("", "dim"))
                        name = t.get('title', tid).replace("[", r"\[")
                        lines += f"  [{colour}]\u25cf[/] {name}\n"
                    else:
                        lines += f"  [dim]\u25cb {tid}[/]\n"
            return lines

    class NavBar(Static):
        """Bottom navigation hints."""

        def __init__(self, index: int, total: int, has_children: bool = False, has_parent_view: bool = False, **kwargs):
            super().__init__(**kwargs)
            self.index = index
            self.total = total
            self.has_children = has_children
            self.has_parent_view = has_parent_view

        def render(self):
            lines = f"\n  [bold]\u25c0 Skip    {self.index + 1} of {self.total}    Add to today \u25b6[/]\n"
            hints = r"  [dim]\[ESC] Quit  \[TAB] Today list  \[d] Done  \[\u2191\u2193] Navigate"
            if self.has_children:
                hints += r"  \[Enter] Drill in"
            if self.has_parent_view:
                hints += r"  \[BS] Back"
            hints += "[/]\n"
            lines += hints
            return lines

    class TaskPickerApp(App):
        """Keyboard-driven task triage TUI."""

        CSS = """
        Screen {
            layout: horizontal;
        }
        #main-panel {
            width: 3fr;
            height: 100%;
        }
        #sidebar {
            width: 1fr;
            min-width: 30;
            height: 100%;
            border-left: solid $accent;
            display: none;
        }
        #sidebar.visible {
            display: block;
        }
        #title-bar {
            dock: top;
            height: 3;
            background: $boost;
            padding: 1 2;
        }
        #card-area {
            height: 1fr;
            padding: 1 2;
        }
        #nav-bar {
            dock: bottom;
            height: 4;
            background: $boost;
        }
        """

        BINDINGS = [
            Binding("escape", "quit_save", "Save & quit", priority=True),
            Binding("q", "quit_save", "Quit", show=False),
            Binding("right", "add_today", "Add to today"),
            Binding("l", "add_today", show=False),
            Binding("left", "skip", "Skip"),
            Binding("h", "skip", show=False),
            Binding("down", "next_task", "Next"),
            Binding("j", "next_task", show=False),
            Binding("up", "prev_task", "Prev"),
            Binding("k", "prev_task", show=False),
            Binding("tab", "toggle_sidebar", "Today list"),
            Binding("d", "mark_done", "Done"),
            Binding("enter", "drill_in", "Drill in"),
            Binding("backspace", "zoom_out", "Back"),
        ]

        def __init__(self):
            super().__init__()
            self.all_tasks = load_tasks()
            self.today_ids = load_today_list()
            self.view_stack: list[Optional[str]] = [None]  # [None] = root view
            self.tasks = filter_tasks_for_view(self.all_tasks, None)
            self.current_index = 0
            self.sidebar_visible = False

        def compose(self) -> ComposeResult:
            yield Vertical(
                Static(id="title-bar"),
                Static(id="card-area"),
                Static(id="nav-bar"),
                id="main-panel",
            )
            yield Vertical(
                Static(id="sidebar-content"),
                id="sidebar",
            )

        def on_mount(self):
            self._refresh_all()

        def _refresh_all(self):
            # Title bar with breadcrumb
            title_bar = self.query_one("#title-bar", Static)
            today_count = len(self.today_ids)
            breadcrumb = "TASK PICKER"
            current_parent = self.view_stack[-1]
            if current_parent:
                task_map = {t.get("id"): t for t in self.all_tasks}
                parent_task = task_map.get(current_parent)
                parent_title = parent_task.get("title", current_parent) if parent_task else current_parent
                breadcrumb += f" > {parent_title}"
            title_bar.update(
                f"  [bold]{breadcrumb}[/]          [green]Today: {today_count} task{'s' if today_count != 1 else ''}[/]"
            )

            # Card area
            card_area = self.query_one("#card-area", Static)
            if not self.tasks:
                if current_parent:
                    card_area.update("[dim]\n  No subtasks. Press Backspace to go back.\n[/]")
                else:
                    card_area.update("[dim]\n  No active tasks found.\n[/]")
            else:
                task = self.tasks[self.current_index]
                card = TaskCard(task, self.current_index, len(self.tasks))
                card_area.update(card.render())

            # Nav bar
            nav_bar = self.query_one("#nav-bar", Static)
            if self.tasks:
                task = self.tasks[self.current_index]
                has_children = bool(task.get("children"))
                has_parent_view = len(self.view_stack) > 1
                nav = NavBar(self.current_index, len(self.tasks), has_children, has_parent_view)
                nav_bar.update(nav.render())
            else:
                nav_bar.update("")

            # Sidebar
            sidebar_content = self.query_one("#sidebar-content", Static)
            sidebar_widget = TodaySidebar(self.today_ids, self.all_tasks)
            sidebar_content.update(sidebar_widget.render())

        def action_next_task(self):
            if self.tasks:
                self.current_index = (self.current_index + 1) % len(self.tasks)
                self._refresh_all()

        def action_prev_task(self):
            if self.tasks:
                self.current_index = (self.current_index - 1) % len(self.tasks)
                self._refresh_all()

        def action_add_today(self):
            if not self.tasks:
                return
            task = self.tasks[self.current_index]
            tid = task.get("id", "")
            if tid and tid not in self.today_ids:
                self.today_ids.append(tid)
                self.notify(f"Added {tid} to today", severity="information")
            elif tid in self.today_ids:
                self.today_ids.remove(tid)
                self.notify(f"Removed {tid} from today", severity="warning")
            # Advance to next task
            if self.current_index < len(self.tasks) - 1:
                self.current_index += 1
            self._refresh_all()

        def action_skip(self):
            self.action_next_task()

        def action_toggle_sidebar(self):
            sidebar = self.query_one("#sidebar")
            self.sidebar_visible = not self.sidebar_visible
            if self.sidebar_visible:
                sidebar.add_class("visible")
            else:
                sidebar.remove_class("visible")
            self._refresh_all()

        def action_mark_done(self):
            if not self.tasks:
                return
            task = self.tasks[self.current_index]
            tid = task.get("id", "")
            if not tid:
                return

            # Complete via RemindersManager (updates file + Reminders.app)
            try:
                sys.path.insert(0, str(_PROJECT_ROOT / ".claude"))
                from reminders.core.manager import RemindersManager
                manager = RemindersManager()
                manager.complete_reminder(tid)
                self.notify(f"{tid} done", severity="information")
            except Exception as e:
                self.notify(f"Error: {e}", severity="error")
                return

            # Remove from today list if present
            if tid in self.today_ids:
                self.today_ids.remove(tid)

            # Remove from in-memory list and adjust index
            self.tasks.pop(self.current_index)
            if self.current_index >= len(self.tasks) and self.tasks:
                self.current_index = len(self.tasks) - 1
            self._refresh_all()

        def action_drill_in(self):
            if not self.tasks:
                return
            task = self.tasks[self.current_index]
            children = task.get("children", [])
            if not children:
                return
            tid = task.get("id", "")
            if not tid:
                return
            self.view_stack.append(tid)
            self.tasks = filter_tasks_for_view(self.all_tasks, tid)
            self.current_index = 0
            self._refresh_all()

        def action_zoom_out(self):
            if len(self.view_stack) <= 1:
                return
            self.view_stack.pop()
            parent_id = self.view_stack[-1]
            self.tasks = filter_tasks_for_view(self.all_tasks, parent_id)
            self.current_index = 0
            self._refresh_all()

        def action_quit_save(self):
            save_today_list(self.today_ids)
            self.exit()


# ---------------------------------------------------------------------------
# Fallback: simple curses TUI if textual is unavailable
# ---------------------------------------------------------------------------

def _curses_fallback():
    """Minimal curses-based picker for environments without textual."""
    import curses

    all_tasks = load_tasks()
    today_ids = load_today_list()
    view_stack = [None]  # [None] = root view
    tasks = filter_tasks_for_view(all_tasks, None)
    idx = 0

    def draw(stdscr):
        nonlocal idx, tasks, view_stack
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
        curses.init_pair(3, curses.COLOR_CYAN, -1)
        curses.init_pair(4, curses.COLOR_GREEN, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)

        q_colour = {"q1": 1, "q2": 2, "q3": 3, "q4": 0}

        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()

            # Title with breadcrumb
            breadcrumb = "TASK PICKER"
            current_parent = view_stack[-1]
            if current_parent:
                task_map = {t.get("id"): t for t in all_tasks}
                parent_task = task_map.get(current_parent)
                parent_title = parent_task.get("title", current_parent) if parent_task else current_parent
                breadcrumb += f" > {parent_title}"
            title = f" {breadcrumb}          Today: {len(today_ids)} tasks "
            stdscr.addstr(0, 0, "\u2554" + "\u2550" * (w - 2) + "\u2557")
            stdscr.addstr(1, 0, "\u2551" + title[:w - 2].ljust(w - 2) + "\u2551")
            stdscr.addstr(2, 0, "\u2560" + "\u2550" * (w - 2) + "\u2563")

            if not tasks:
                if current_parent:
                    stdscr.addstr(4, 2, "No subtasks. Press Backspace to go back.")
                else:
                    stdscr.addstr(4, 2, "No active tasks found.")
            else:
                t = tasks[idx]
                q = t.get("eisenhower_quadrant", "q4")
                label, _ = QUADRANT_LABEL.get(q, ("Q4", ""))
                cp = curses.color_pair(q_colour.get(q, 0))

                row = 4
                stdscr.addstr(row, 3, label, cp | curses.A_BOLD)
                badge_col = 3 + len(label) + 3
                if t.get("_overdue"):
                    stdscr.addstr(row, badge_col, "OVERDUE", curses.color_pair(1) | curses.A_BOLD)
                    badge_col += 10
                elif t.get("_due_today"):
                    stdscr.addstr(row, badge_col, "DUE TODAY", curses.color_pair(2) | curses.A_BOLD)
                    badge_col += 12

                # Hierarchy badges
                children = t.get("children", [])
                if children:
                    child_badge = f"[{len(children)} subtask{'s' if len(children) != 1 else ''}]"
                    if badge_col + len(child_badge) < w - 2:
                        stdscr.addstr(row, badge_col, child_badge, curses.color_pair(5) | curses.A_BOLD)
                        badge_col += len(child_badge) + 3

                row += 2
                title_str = t.get("title", "Untitled")[:w - 6]
                stdscr.addstr(row, 3, title_str, curses.A_BOLD)

                row += 2
                meta = f"{t.get('id', '???')}  \u00b7  {t.get('priority', 'low')}"
                if "_due_date" in t:
                    meta += f"  \u00b7  due: {t['_due_date'].strftime('%d %b')}"
                if t.get("parent"):
                    meta += f"  \u00b7  parent: {t['parent']}"
                if t.get("prd"):
                    meta += f"  \u00b7  PRD: {t['prd']}"
                stdscr.addstr(row, 3, meta[:w - 6])

                row += 2
                desc = t.get("_description", "")[:w * 3]
                for line in desc.split("\n")[:5]:
                    if row < h - 5:
                        stdscr.addstr(row, 3, line[:w - 6])
                        row += 1

                # Today marker
                tid = t.get("id", "")
                if tid in today_ids:
                    stdscr.addstr(4, w - 12, " TODAY ", curses.color_pair(4) | curses.A_REVERSE)

            # Bottom nav
            nav_row = h - 3
            stdscr.addstr(nav_row - 1, 0, "\u2560" + "\u2550" * (w - 2) + "\u2563")
            if tasks:
                nav = f" \u25c0 Skip    {idx + 1} of {len(tasks)}    Add to today \u25b6 "
                stdscr.addstr(nav_row, 2, nav, curses.A_BOLD)
            nav_hints = "[ESC] Quit  [TAB] Today  [d] Done  [\u2191\u2193] Navigate"
            if tasks and tasks[idx].get("children"):
                nav_hints += "  [Enter] Drill in"
            if len(view_stack) > 1:
                nav_hints += "  [BS] Back"
            stdscr.addstr(nav_row + 1, 2, nav_hints[:w - 4])
            stdscr.addstr(h - 1, 0, "\u255a" + "\u2550" * (w - 2) + "\u255d")

            stdscr.refresh()
            key = stdscr.getch()

            if key in (27, ord('q')):  # ESC or q
                break
            elif key in (curses.KEY_DOWN, ord('j')):
                idx = (idx + 1) % max(len(tasks), 1)
            elif key in (curses.KEY_UP, ord('k')):
                idx = (idx - 1) % max(len(tasks), 1)
            elif key in (curses.KEY_RIGHT, ord('l')):
                if tasks:
                    tid = tasks[idx].get("id", "")
                    if tid and tid not in today_ids:
                        today_ids.append(tid)
                    elif tid in today_ids:
                        today_ids.remove(tid)
                    if idx < len(tasks) - 1:
                        idx += 1
            elif key in (curses.KEY_LEFT, ord('h')):
                idx = (idx + 1) % max(len(tasks), 1)
            elif key == 10:  # Enter — drill into children
                if tasks:
                    children = tasks[idx].get("children", [])
                    tid = tasks[idx].get("id", "")
                    if children and tid:
                        view_stack.append(tid)
                        tasks = filter_tasks_for_view(all_tasks, tid)
                        idx = 0
            elif key in (127, curses.KEY_BACKSPACE, 8):  # Backspace — zoom out
                if len(view_stack) > 1:
                    view_stack.pop()
                    parent_id = view_stack[-1]
                    tasks = filter_tasks_for_view(all_tasks, parent_id)
                    idx = 0
            elif key == ord('d'):
                if tasks:
                    tid = tasks[idx].get("id", "")
                    if tid:
                        try:
                            sys.path.insert(0, str(_PROJECT_ROOT / ".claude"))
                            from reminders.core.manager import RemindersManager
                            manager = RemindersManager()
                            manager.complete_reminder(tid)
                        except Exception:
                            pass
                        if tid in today_ids:
                            today_ids.remove(tid)
                        tasks.pop(idx)
                        if idx >= len(tasks) and tasks:
                            idx = len(tasks) - 1
            elif key == 9:  # TAB — simple today list display
                stdscr.clear()
                stdscr.addstr(0, 2, "TODAY LIST", curses.A_BOLD | curses.color_pair(4))
                stdscr.addstr(1, 2, "-" * 30)
                if not today_ids:
                    stdscr.addstr(3, 2, "(empty)")
                else:
                    task_map = {t["id"]: t for t in all_tasks if "id" in t}
                    for i, tid in enumerate(today_ids):
                        t = task_map.get(tid)
                        name = t.get("title", tid) if t else tid
                        stdscr.addstr(3 + i, 2, f"  {tid}: {name}"[:w - 4])
                stdscr.addstr(h - 2, 2, "Press any key to return...")
                stdscr.refresh()
                stdscr.getch()

        save_today_list(today_ids)

    curses.wrapper(draw)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if HAS_TEXTUAL:
        app = TaskPickerApp()
        app.run()
    else:
        _curses_fallback()
