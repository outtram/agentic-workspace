"""Task edit modal — inline editing of task fields."""
from pathlib import Path

import yaml
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Button, Static, TextArea, RadioSet, RadioButton

from . import PROJECT_ROOT

_TASK_DIR = PROJECT_ROOT / ".claude" / "work" / "tasks"

_QUADRANTS = ("q1", "q2", "q3", "q4")
_PRIORITIES = ("low", "medium", "high")


class TaskEditScreen(ModalScreen[bool]):
    """Modal for editing a task's fields."""

    DEFAULT_CSS = """
    TaskEditScreen {
        align: center middle;
    }
    #edit-box {
        width: 60;
        max-height: 90%;
        background: #1a1a1a;
        border: solid #FF6B35;
        padding: 1 2;
        overflow-y: auto;
    }
    #edit-title {
        margin-bottom: 1;
    }
    .field-label {
        margin-top: 1;
        color: #777777;
    }
    #edit-input-title, #edit-input-due, #edit-input-parent {
        margin-bottom: 0;
    }
    #edit-description {
        height: 8;
        margin-bottom: 1;
    }
    RadioSet {
        height: 3;
        margin-bottom: 0;
    }
    #button-row {
        height: 3;
        margin-top: 1;
        align: center middle;
    }
    #btn-save {
        margin-right: 2;
    }
    """

    def __init__(self, task: dict):
        super().__init__()
        self._task_data = task
        self.task_id = task.get("id", "")

    def compose(self):
        with VerticalScroll(id="edit-box"):
            yield Static(
                f"[bold #FF6B35]EDIT TASK: {self.task_id}[/]",
                id="edit-title",
            )

            yield Static("[dim]Title[/]", classes="field-label")
            yield Input(
                value=self._task_data.get("title", ""),
                id="edit-input-title",
            )

            yield Static("[dim]Quadrant[/]", classes="field-label")
            current_q = self._task_data.get("eisenhower_quadrant", "q4")
            with RadioSet(id="edit-quadrant"):
                for q in _QUADRANTS:
                    yield RadioButton(
                        q.upper(),
                        value=q == current_q,
                        name=q,
                    )

            yield Static("[dim]Priority[/]", classes="field-label")
            current_p = self._task_data.get("priority", "low")
            with RadioSet(id="edit-priority"):
                for p in _PRIORITIES:
                    yield RadioButton(
                        p.capitalize(),
                        value=p == current_p,
                        name=p,
                    )

            yield Static("[dim]Due date (YYYY-MM-DD)[/]", classes="field-label")
            due = self._task_data.get("due_date", "")
            if hasattr(due, "isoformat"):
                due = due.isoformat()
            yield Input(
                value=str(due) if due else "",
                id="edit-input-due",
            )

            yield Static("[dim]Parent[/]", classes="field-label")
            yield Input(
                value=self._task_data.get("parent", "") or "",
                id="edit-input-parent",
            )

            yield Static("[dim]Description[/]", classes="field-label")
            yield TextArea(
                self._task_data.get("_description", ""),
                id="edit-description",
            )

            with Horizontal(id="button-row"):
                yield Button("Save", variant="success", id="btn-save")
                yield Button("Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._save()
            self.dismiss(True)
        else:
            self.dismiss(False)

    def _get_selected_name(self, radio_set_id: str, options: tuple) -> str:
        """Get the name of the selected radio button in a set."""
        try:
            rs = self.query_one(f"#{radio_set_id}", RadioSet)
            idx = rs.pressed_index
            if idx >= 0 and idx < len(options):
                return options[idx]
        except Exception:
            pass
        return options[-1]

    def _save(self) -> None:
        """Write updated fields back to the task's markdown file."""
        task_file = _TASK_DIR / f"{self.task_id}.md"
        if not task_file.exists():
            return

        content = task_file.read_text()
        parts = content.split("---", 2)
        if len(parts) < 3:
            return

        try:
            meta = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            return
        if not isinstance(meta, dict):
            return

        # Read form values
        new_title = self.query_one("#edit-input-title", Input).value.strip()
        new_due = self.query_one("#edit-input-due", Input).value.strip()
        new_parent = self.query_one("#edit-input-parent", Input).value.strip()
        new_desc = self.query_one("#edit-description", TextArea).text.strip()
        new_quadrant = self._get_selected_name("edit-quadrant", _QUADRANTS)
        new_priority = self._get_selected_name("edit-priority", _PRIORITIES)

        # Update frontmatter
        if new_title:
            meta["title"] = new_title
        meta["eisenhower_quadrant"] = new_quadrant
        meta["eisenhower_urgent"] = new_quadrant in ("q1", "q3")
        meta["eisenhower_important"] = new_quadrant in ("q1", "q2")
        meta["priority"] = new_priority
        meta["due_date"] = new_due if new_due else None
        if new_parent:
            meta["parent"] = new_parent
        elif "parent" in meta:
            del meta["parent"]

        # Rebuild file
        body = parts[2]
        new_body = self._update_description_section(body, new_desc)
        new_frontmatter = yaml.dump(
            meta, default_flow_style=False, sort_keys=False, allow_unicode=True
        )
        task_file.write_text(f"---\n{new_frontmatter}---{new_body}")

    def _update_description_section(self, body: str, new_desc: str) -> str:
        """Replace or insert the ## Description section in the body."""
        lines = body.split("\n")
        new_lines = []
        in_desc = False
        desc_replaced = False

        for line in lines:
            if line.startswith("## Description"):
                new_lines.append(line)
                new_lines.append("")
                new_lines.append(new_desc)
                new_lines.append("")
                in_desc = True
                desc_replaced = True
                continue
            if in_desc:
                if line.startswith("##"):
                    in_desc = False
                    new_lines.append(line)
                continue
            new_lines.append(line)

        if not desc_replaced:
            new_lines.append("")
            new_lines.append("## Description")
            new_lines.append("")
            new_lines.append(new_desc)
            new_lines.append("")

        return "\n".join(new_lines)
