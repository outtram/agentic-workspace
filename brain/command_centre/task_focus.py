"""Task Focus View — single-task control centre with field-by-field editing.

When the user presses Enter on a leaf task (no children), this view takes
over the grid area.  Arrow keys navigate between fields, Enter edits inline,
Escape backs out one level.
"""

import re
import yaml
from datetime import datetime
from pathlib import Path

from textual.widget import Widget
from textual.widgets import Static, Input, TextArea

from .sanitiser import sanitise
from .task_loader import (
    QUADRANT_COLOURS,
    QUADRANT_LABELS,
    find_task_file,
)

_PRD_DIR = Path(__file__).resolve().parent.parent.parent / ".claude" / "work" / "prd"


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

        Extra positions past the fields: PRD, then Notes/Research.
        """
        if self._editing:
            return
        new = self._field_cursor + direction
        # len(_FIELDS) = PRD, len(_FIELDS)+1 = notes/research
        if 0 <= new <= len(_FIELDS) + 1:
            self._field_cursor = new
            self._refresh_display()

    def start_edit(self) -> None:
        """Enter edit mode for the currently focused field."""
        if not self._task_data or self._editing:
            return

        # PRD section — open or create PRD
        if self._field_cursor == len(_FIELDS):
            self.open_or_create_prd()
            return

        # Notes/research section — open full content read-only
        if self._field_cursor == len(_FIELDS) + 1:
            self._editing = True
            self._edit_field = "_notes_research"
            self._show_textarea("_notes_research")
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

    def start_add_note(self) -> None:
        """Open a blank textarea to add a new note."""
        if not self._task_data or self._editing:
            return
        self._editing = True
        self._edit_field = "_new_note"
        self._show_textarea("_new_note")

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

        # Notes/research viewer is read-only — just close
        if key == "_notes_research":
            self._editing = False
            self._edit_field = None
            self._hide_editors()
            self._refresh_display()
            return

        # New note — append timestamped section to task file
        if key == "_new_note":
            if value.strip():
                self._append_note(value.strip())
            self._editing = False
            self._edit_field = None
            self._hide_editors()
            self._refresh_display()
            return

        # PRD — save content back to PRD file
        if key == "_prd":
            if value.strip():
                self._save_prd(value)
            self._editing = False
            self._edit_field = None
            self._hide_editors()
            self._refresh_display()
            return

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
        prd_badge = ""
        if task.get("prd"):
            prd_badge = f"  [bold blue]PRD[/]"
        lines.append(
            f"[bold #FF6B35]{tid}[/]  [{colour}]{label}[/]{prd_badge}"
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

        # PRD section (cursor position = len(_FIELDS))
        prd_pos = len(_FIELDS)
        prd_focused = self._field_cursor == prd_pos and not self._editing
        prd_id = task.get("prd", "")
        lines.append("")
        prd_arrow = "[bold #FF6B35]\u25b8 [/]" if prd_focused else "  "
        if prd_id:
            prd_hint = " [dim](p to edit)[/]" if prd_focused else ""
            lines.append(f"{prd_arrow}[bold blue]PRD[/]  {prd_id}{prd_hint}")
        else:
            prd_hint = " [dim](p to create)[/]" if prd_focused else ""
            lines.append(f"{prd_arrow}[dim]No PRD[/]{prd_hint}")

        # Notes section (cursor position = len(_FIELDS) + 1)
        notes_pos = prd_pos + 1
        notes_focused = self._field_cursor == notes_pos and not self._editing
        lines.append("")
        lines.append("[#333333]" + "\u2501" * 48 + "[/]")
        notes = self._get_notes()
        arrow = "[bold #FF6B35]\u25b8 [/]" if notes_focused else "  "
        hint = " [dim](Enter to view)[/]" if notes_focused else ""
        if notes:
            lines.append(f"{arrow}[bold]NOTES & RESEARCH[/]{hint}")
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
            "[bold #FF6B35]n[/][dim] Note  [/]"
            "[bold #FF6B35]p[/][dim] PRD  [/]"
            "[bold #FF6B35]t[/][dim] Today  [/]"
            "[bold #FF6B35]d[/][dim] Done  [/]"
        )

        try:
            self.query_one("#focus-content", Static).update("\n".join(lines))
        except Exception:
            pass

    def _get_display_value(self, key: str) -> str:
        """Get the display string for a field."""
        if key == "_new_note":
            return ""
        if key == "_prd":
            return self._get_prd_content()
        if not self._task_data:
            return ""
        if key == "_notes_research":
            return self._get_full_research()
        val = self._task_data.get(key, "")
        if val is None:
            return ""
        if key == "due_date" and hasattr(val, "isoformat"):
            return val.isoformat()
        if key == "_due_date":
            return str(val) if val else ""
        result = str(val)
        if key in ("title", "_description"):
            result = sanitise(result)
        return result

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
            area.read_only = key == "_notes_research"
            # Size based on content type
            if key == "_prd":
                area.styles.height = 24
            elif key in ("_notes_research", "_new_note"):
                area.styles.height = 16
            else:
                area.styles.height = 8
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
            area = self.query_one("#focus-edit-area", TextArea)
            area.styles.display = "none"
            area.read_only = False
            area.styles.height = 8
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
                    # Show first 3 non-blank content lines as preview
                    entries.append("Research findings:")
                    j = i + 1
                    shown = 0
                    while j < len(lines) and shown < 3:
                        if self._is_section_boundary(lines[j]) and not lines[j].startswith("## Research"):
                            break
                        text = lines[j].strip()
                        # Skip blank lines and markdown separators
                        if text and text != "---":
                            entries.append(f"  {text[:60]}")
                            shown += 1
                        j += 1
                i += 1
            return entries
        except Exception:
            return []

    # Known task file section headings (research content may have its own ## headings)
    _SECTION_HEADINGS = {"Description", "Steps", "Notes", "Research", "Note"}

    def _is_section_boundary(self, line: str) -> bool:
        """Check if a line is a known task-file section heading."""
        if not line.startswith("## "):
            return False
        heading = line[3:].split()[0] if line[3:].strip() else ""
        return heading in self._SECTION_HEADINGS

    def _get_full_research(self) -> str:
        """Get full research + notes content from the task file."""
        if not self._task_data:
            return ""
        task_id = self._task_data.get("id", "")
        if not task_id:
            return ""
        task_file = find_task_file(task_id)
        if not task_file:
            return ""
        try:
            content = task_file.read_text()
            sections: list[str] = []
            lines = content.split("\n")
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.startswith("## Research") or line.startswith("## Note"):
                    section_lines = [line]
                    i += 1
                    # Capture everything until the next known section boundary
                    while i < len(lines):
                        if self._is_section_boundary(lines[i]) and lines[i] != line:
                            break
                        section_lines.append(lines[i])
                        i += 1
                    sections.append("\n".join(section_lines).strip())
                    continue
                i += 1
            return "\n\n".join(sections) if sections else "(no notes or research)"
        except Exception:
            return ""

    def _append_note(self, text: str) -> None:
        """Append a timestamped note section to the task file."""
        if not self._task_data:
            return
        task_id = self._task_data.get("id", "")
        if not task_id:
            return
        task_file = find_task_file(task_id)
        if not task_file:
            return
        try:
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            section = f"\n\n## Note — {stamp}\n\n{text}\n"
            content = task_file.read_text().rstrip()
            task_file.write_text(content + section)
            try:
                self.app.notify("Note added")
            except Exception:
                pass
        except Exception as e:
            try:
                self.app.notify(f"Note failed: {e}", severity="error")
            except Exception:
                pass

    # --- PRD support ---

    def _find_prd_file(self) -> Path | None:
        """Find the PRD file linked to this task."""
        if not self._task_data:
            return None
        prd_id = self._task_data.get("prd", "")
        if not prd_id:
            return None
        matches = list(_PRD_DIR.glob(f"{prd_id}-*.md"))
        if matches:
            return matches[0]
        exact = _PRD_DIR / f"{prd_id}.md"
        if exact.exists():
            return exact
        return None

    def _get_prd_content(self) -> str:
        """Read the full PRD content."""
        prd_file = self._find_prd_file()
        if not prd_file:
            return ""
        try:
            return prd_file.read_text()
        except Exception:
            return ""

    def _create_prd(self) -> str | None:
        """Create a new PRD from the task, link it, return the PRD ID."""
        if not self._task_data:
            return None
        task_id = self._task_data.get("id", "")
        title = self._task_data.get("title", "Untitled")
        desc = self._task_data.get("_description", "")
        priority = self._task_data.get("priority", "medium")

        # Generate PRD ID from task ID
        prd_id = task_id
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
        filename = f"{prd_id}-{slug}.md"
        prd_path = _PRD_DIR / filename

        if prd_path.exists():
            return prd_id

        # Pull existing research + notes from the task file
        existing_context = self._get_full_research()
        notes_section = "Additional context, links, research."
        if existing_context and existing_context != "(no notes or research)":
            notes_section = existing_context

        now = datetime.now().strftime("%Y-%m-%d")
        content = f"""---
id: {prd_id}
title: {title}
type: prd
status: draft
priority: {priority}
created: {now}
updated: {now}
assignee: Troy
branch: feature/{prd_id}-{slug}
---

# {title}

## Problem
{desc if desc else 'What problem does this solve?'}

## Solution
What are we building?

## Requirements
- [ ] Requirement 1
- [ ] Requirement 2

## Design Notes
Any design decisions, mockups, or technical approaches.

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Related
- Parent task: {task_id}

## Notes
{notes_section}

## Progress Log
- {now}: Created PRD from task {task_id}
"""
        try:
            _PRD_DIR.mkdir(parents=True, exist_ok=True)
            prd_path.write_text(content)
        except Exception as e:
            try:
                self.app.notify(f"PRD create failed: {e}", severity="error")
            except Exception:
                pass
            return None

        # Link PRD to task file
        self._task_data["prd"] = prd_id
        self._dirty = True
        self._save_to_file()

        return prd_id

    def open_or_create_prd(self) -> None:
        """Open existing PRD or create a new one, then show in editor."""
        if not self._task_data or self._editing:
            return

        prd_id = self._task_data.get("prd", "")
        if not prd_id:
            prd_id = self._create_prd()
            if not prd_id:
                return
            try:
                self.app.notify(f"PRD created: {prd_id}")
            except Exception:
                pass

        # Open PRD in the textarea for editing
        self._editing = True
        self._edit_field = "_prd"
        self._show_textarea("_prd")

    def _save_prd(self, content: str) -> None:
        """Write PRD content back to the file."""
        prd_file = self._find_prd_file()
        if not prd_file:
            return
        try:
            prd_file.write_text(content)
            try:
                self.app.notify("PRD saved")
            except Exception:
                pass
        except Exception as e:
            try:
                self.app.notify(f"PRD save failed: {e}", severity="error")
            except Exception:
                pass

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

            prd = task.get("prd", "")
            if prd:
                meta["prd"] = prd
            elif "prd" in meta:
                del meta["prd"]

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
