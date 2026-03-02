"""Task Focus View — single-task control centre with field-by-field editing.

When the user presses Enter on a leaf task (no children), this view takes
over the grid area.  Arrow keys navigate between fields, Enter edits inline,
Escape backs out one level.
"""

import yaml
from datetime import datetime

from textual.widget import Widget
from textual.widgets import Static, Input, TextArea

from .sanitiser import sanitise
from .task_loader import (
    QUADRANT_COLOURS,
    QUADRANT_LABELS,
    find_task_file,
)


# Fields shown in the focus view, in order.
# Each tuple: (key, label, field_type)
#   field_type: "text" = single line, "choice" = cycle, "multiline" = textarea
_FIELDS = [
    ("title", "TITLE", "text"),
    ("eisenhower_quadrant", "QUADRANT", "choice"),
    ("priority", "PRIORITY", "choice"),
    ("due_date", "DUE DATE", "text"),
    ("status", "STATUS", "choice"),
    ("parent", "PARENT", "text"),
    ("_description", "DESCRIPTION", "multiline"),
]

_QUADRANT_CYCLE = ["q1", "q2", "q3", "q4"]
_PRIORITY_CYCLE = ["low", "medium", "high"]
_STATUS_CYCLE = ["todo", "open", "draft", "doing"]


class TaskFocusView(Widget):
    """Displays a single task with editable fields.

    Managed by the main app — not a standalone screen.  The app toggles
    visibility and forwards key events.
    """

    DEFAULT_CSS = """
    TaskFocusView {
        width: 3fr;
        padding: 1 2;
        display: none;
        layout: vertical;
        overflow-y: auto;
    }
    #focus-content {
        width: 100%;
    }
    #focus-edit-input {
        display: none;
        margin: 0 0 0 14;
        width: 1fr;
        background: #222222;
        border: solid #FF6B35;
    }
    #focus-edit-input:focus {
        background: #2a2a2a;
    }
    #focus-edit-area {
        display: none;
        margin: 0 0 0 2;
        height: 8;
        width: 1fr;
        background: #222222;
        border: solid #FF6B35;
    }
    #focus-edit-area:focus {
        background: #2a2a2a;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._task_data: dict | None = None
        self._field_cursor: int = 0
        self._editing: bool = False
        self._edit_field: str | None = None
        self._dirty: bool = False
        self._save_timer = None

    def compose(self):
        yield Static(id="focus-content")
        yield Input(id="focus-edit-input")
        yield TextArea(id="focus-edit-area")

    @property
    def task(self) -> dict | None:
        return self._task_data

    @property
    def is_editing(self) -> bool:
        return self._editing

    @property
    def field_cursor(self) -> int:
        return self._field_cursor

    def show_task(self, task: dict) -> None:
        """Set the task and render the focus view."""
        self._task_data = task
        self._field_cursor = 0
        self._editing = False
        self._edit_field = None
        self._dirty = False
        self._hide_editors()
        self._refresh_display()

    def clear(self) -> None:
        """Clear the focus view and release any editor focus."""
        self._task_data = None
        self._field_cursor = 0
        self._editing = False
        self._edit_field = None
        self._hide_editors()
        # Blur any focused child widget so keys return to the app
        try:
            self.app.screen.set_focus(None)
        except Exception:
            pass

    def move_cursor(self, direction: int) -> None:
        """Move field cursor up (-1) or down (+1).

        Cursor can go one past the last field to highlight the notes section.
        """
        if self._editing:
            return
        new = self._field_cursor + direction
        # len(_FIELDS) = notes/research section (one past last field)
        if 0 <= new <= len(_FIELDS):
            self._field_cursor = new
            self._refresh_display()

    def start_edit(self) -> None:
        """Enter edit mode for the currently focused field."""
        if not self._task_data or self._editing:
            return
        # Notes section is read-only
        if self._field_cursor >= len(_FIELDS):
            return

        key, _label, field_type = _FIELDS[self._field_cursor]
        self._editing = True
        self._edit_field = key

        if field_type == "choice":
            # Cycle to next value immediately
            self._cycle_choice(key)
            self._editing = False
            self._edit_field = None
            self._refresh_display()
            return

        if field_type == "multiline":
            self._show_textarea(key)
        else:
            self._show_input(key)

    def cancel_edit(self) -> bool:
        """Cancel current edit.  Returns True if was editing (consumed Esc)."""
        if not self._editing:
            return False
        self._editing = False
        self._edit_field = None
        self._hide_editors()
        self._refresh_display()
        return True

    def commit_edit(self, value: str) -> None:
        """Save the edited value back to the task dict (and to file)."""
        if not self._task_data or not self._edit_field:
            return

        key = self._edit_field
        old_val = self._get_display_value(key)

        if value.strip() != old_val.strip():
            self._task_data[key] = value.strip()
            self._dirty = True
            self._save_to_file()

        self._editing = False
        self._edit_field = None
        self._hide_editors()
        self._refresh_display()

    def handle_input_submitted(self, value: str) -> None:
        """Called when the inline Input is submitted."""
        self.commit_edit(value)

    def handle_textarea_escape(self) -> None:
        """Called when Escape is pressed in the textarea — save and close."""
        try:
            area = self.query_one("#focus-edit-area", TextArea)
            self.commit_edit(area.text)
        except Exception:
            self.cancel_edit()

    # --- Internal rendering ---

    def _refresh_display(self) -> None:
        """Re-render the focus view content."""
        if not self._task_data:
            return

        task = self._task_data
        tid = task.get("id", "???")
        q = task.get("eisenhower_quadrant", "q4")
        colour = QUADRANT_COLOURS.get(q, "#3D3D3D")
        label = QUADRANT_LABELS.get(q, "Q4")

        lines: list[str] = []

        # Header
        lines.append(
            f"[bold #FF6B35]{tid}[/]  [{colour}]{label}[/]"
        )
        lines.append(f"[dim]← Esc back to grid[/]")
        lines.append("[#333333]" + "\u2501" * 48 + "[/]")
        lines.append("")

        # Fields
        for idx, (key, field_label, field_type) in enumerate(_FIELDS):
            is_cursor = idx == self._field_cursor and not self._editing
            is_editing_this = self._editing and self._edit_field == key
            value = self._get_display_value(key)

            # Format the value with colour for special fields
            display_value = self._format_value(key, value)

            if is_editing_this:
                # Show placeholder — actual editor widget is separate
                row = f"  [bold #FF6B35]\u25b8 {field_label:<12}[/] [dim]editing...[/]"
            elif is_cursor:
                arrow = "\u25b8"
                if field_type == "choice":
                    hint = " [dim](Enter to cycle)[/]"
                elif field_type == "multiline":
                    hint = " [dim](Enter to edit)[/]"
                else:
                    hint = " [dim](Enter to edit)[/]"
                row = f"  [bold #FF6B35]{arrow} {field_label:<12}[/] {display_value}{hint}"
            else:
                row = f"    {field_label:<12} {display_value}"

            lines.append(row)

            # For description, show preview below the field
            if key == "_description" and not is_editing_this:
                desc = value
                if desc:
                    preview = desc[:200].replace("[", r"\[")
                    for pline in preview.split("\n")[:4]:
                        lines.append(f"    {' ' * 12} [dim]{pline}[/]")
                    if len(desc) > 200:
                        lines.append(f"    {' ' * 12} [dim]...[/]")
                else:
                    lines.append(f"    {' ' * 12} [dim](no description)[/]")

        # Notes section (read-only, cursor position = len(_FIELDS))
        notes_focused = self._field_cursor == len(_FIELDS) and not self._editing
        lines.append("")
        lines.append("[#333333]" + "\u2501" * 48 + "[/]")
        notes = self._get_notes()
        arrow = "[bold #FF6B35]\u25b8 [/]" if notes_focused else "  "
        if notes:
            lines.append(f"{arrow}[bold]NOTES & RESEARCH[/]")
            for note in notes[-6:]:
                safe_note = note.replace("[", r"\[")
                lines.append(f"    {safe_note}")
        else:
            lines.append(f"{arrow}[dim]No notes yet[/]")

        # Hints
        lines.append("")
        lines.append("[#333333]" + "\u2501" * 48 + "[/]")
        lines.append(
            "[bold #FF6B35]/[/][dim] Commands  [/]"
            "[bold #FF6B35]t[/][dim] Today  [/]"
            "[bold #FF6B35]d[/][dim] Done  [/]"
            "[bold #FF6B35]Space[/][dim] Select[/]"
        )

        try:
            self.query_one("#focus-content", Static).update("\n".join(lines))
        except Exception:
            pass

    def _get_display_value(self, key: str) -> str:
        """Get the display string for a field."""
        if not self._task_data:
            return ""
        val = self._task_data.get(key, "")
        if val is None:
            return ""
        if key == "due_date" and hasattr(val, "isoformat"):
            return val.isoformat()
        if key == "_due_date":
            return str(val) if val else ""
        return str(val)

    def _format_value(self, key: str, value: str) -> str:
        """Add colour formatting for specific fields."""
        if not value:
            return "[dim](empty)[/]"

        safe = value.replace("[", r"\[")

        if key == "eisenhower_quadrant":
            colour = QUADRANT_COLOURS.get(value, "#3D3D3D")
            label = QUADRANT_LABELS.get(value, value.upper())
            return f"[{colour}]{label}[/]"
        elif key == "priority":
            colours = {"high": "#FF6B35", "medium": "#FFD700", "low": "#777777"}
            c = colours.get(value, "#777777")
            return f"[{c}]{safe}[/]"
        elif key == "status":
            colours = {"todo": "#777777", "open": "#00D4AA", "draft": "#FFD700", "doing": "#FF6B35"}
            c = colours.get(value, "#777777")
            return f"[{c}]{safe}[/]"
        elif key == "_description":
            # Just show first line in the field row
            first_line = value.split("\n")[0][:40]
            if first_line:
                return f"[dim]{first_line.replace('[', chr(92) + '[')}[/]"
            return "[dim](empty)[/]"
        else:
            return safe

    def _cycle_choice(self, key: str) -> None:
        """Cycle a choice field to the next value."""
        if not self._task_data:
            return

        cycles = {
            "eisenhower_quadrant": _QUADRANT_CYCLE,
            "priority": _PRIORITY_CYCLE,
            "status": _STATUS_CYCLE,
        }
        cycle = cycles.get(key)
        if not cycle:
            return

        current = self._task_data.get(key, cycle[0])
        try:
            idx = cycle.index(current)
            new_val = cycle[(idx + 1) % len(cycle)]
        except ValueError:
            new_val = cycle[0]

        self._task_data[key] = new_val

        # Update derived fields for quadrant
        if key == "eisenhower_quadrant":
            self._task_data["eisenhower_urgent"] = new_val in ("q1", "q3")
            self._task_data["eisenhower_important"] = new_val in ("q1", "q2")

        self._dirty = True
        self._debounced_save()

    def _show_input(self, key: str) -> None:
        """Show the inline input for a text field."""
        try:
            inp = self.query_one("#focus-edit-input", Input)
            inp.value = self._get_display_value(key)
            inp.styles.display = "block"
            inp.focus()
        except Exception:
            pass

    def _show_textarea(self, key: str) -> None:
        """Show the textarea for multiline fields."""
        try:
            area = self.query_one("#focus-edit-area", TextArea)
            area.load_text(self._get_display_value(key))
            area.styles.display = "block"
            area.focus()
        except Exception:
            pass

    def _hide_editors(self) -> None:
        """Hide both editor widgets."""
        try:
            self.query_one("#focus-edit-input", Input).styles.display = "none"
        except Exception:
            pass
        try:
            self.query_one("#focus-edit-area", TextArea).styles.display = "none"
        except Exception:
            pass

    def _get_notes(self) -> list[str]:
        """Extract note and research sections from the task file."""
        if not self._task_data:
            return []
        task_id = self._task_data.get("id", "")
        if not task_id:
            return []
        task_file = find_task_file(task_id)
        if not task_file:
            return []
        try:
            content = task_file.read_text()
            entries: list[str] = []
            lines = content.split("\n")
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.startswith("## Note"):
                    entries.append(line.replace("## ", ""))
                elif line.startswith("## Research"):
                    # Show first 3 lines of research content
                    entries.append("Research findings:")
                    j = i + 1
                    # Skip blank lines after heading
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                    shown = 0
                    while j < len(lines) and shown < 3:
                        if lines[j].startswith("##"):
                            break
                        if lines[j].strip():
                            entries.append(f"  {lines[j].strip()[:60]}")
                            shown += 1
                        j += 1
                i += 1
            return entries
        except Exception:
            return []

    def _debounced_save(self) -> None:
        """Debounce file writes — waits 0.5s after last change before saving."""
        if self._save_timer is not None:
            self._save_timer.stop()
        self._save_timer = self.set_timer(0.5, self._save_to_file)

    def _save_to_file(self) -> None:
        """Persist changes back to the task's markdown file."""
        self._save_timer = None
        if not self._task_data:
            return
        task_id = self._task_data.get("id", "")
        if not task_id:
            return

        task_file = find_task_file(task_id)
        if not task_file:
            return

        try:
            content = task_file.read_text()
            parts = content.split("---", 2)
            if len(parts) < 3:
                return

            meta = yaml.safe_load(parts[1])
            if not isinstance(meta, dict):
                return

            # Update frontmatter fields
            task = self._task_data
            if task.get("title"):
                meta["title"] = task["title"]
            meta["eisenhower_quadrant"] = task.get("eisenhower_quadrant", "q4")
            meta["eisenhower_urgent"] = task.get("eisenhower_quadrant", "q4") in ("q1", "q3")
            meta["eisenhower_important"] = task.get("eisenhower_quadrant", "q4") in ("q1", "q2")
            meta["priority"] = task.get("priority", "low")

            due = task.get("due_date", "")
            if hasattr(due, "isoformat"):
                due = due.isoformat()
            meta["due_date"] = due if due else None

            status = task.get("status", "todo")
            meta["status"] = status

            parent = task.get("parent", "")
            if parent:
                meta["parent"] = parent
            elif "parent" in meta:
                del meta["parent"]

            meta["updated"] = datetime.now().isoformat()

            # Rebuild body with updated description
            body = parts[2]
            new_desc = task.get("_description", "")
            body = self._update_description_section(body, new_desc)

            new_fm = yaml.dump(
                meta, default_flow_style=False, sort_keys=False, allow_unicode=True
            )
            task_file.write_text(f"---\n{new_fm}---{body}")
        except Exception as e:
            # Surface save errors via Textual notification
            try:
                self.app.notify(f"Save failed: {e}", severity="error")
            except Exception:
                pass

    @staticmethod
    def _update_description_section(body: str, new_desc: str) -> str:
        """Replace or insert the ## Description section."""
        lines = body.split("\n")
        new_lines = []
        in_desc = False
        replaced = False

        for line in lines:
            if line.startswith("## Description"):
                new_lines.append(line)
                new_lines.append("")
                new_lines.append(new_desc)
                new_lines.append("")
                in_desc = True
                replaced = True
                continue
            if in_desc:
                if line.startswith("##"):
                    in_desc = False
                    new_lines.append(line)
                continue
            new_lines.append(line)

        if not replaced:
            new_lines.append("")
            new_lines.append("## Description")
            new_lines.append("")
            new_lines.append(new_desc)
            new_lines.append("")

        return "\n".join(new_lines)
