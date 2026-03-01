"""Note modal — quick note input for a task."""

from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static, TextArea


class NoteModal(ModalScreen[str | None]):
    """Modal for adding a note to a task."""

    DEFAULT_CSS = """
    NoteModal {
        align: center middle;
    }
    #note-box {
        width: 56;
        height: auto;
        max-height: 70%;
        background: #1a1a1a;
        border: solid #FF6B35;
        padding: 1 2;
    }
    #note-title {
        margin-bottom: 1;
    }
    #note-input {
        height: 8;
        margin-bottom: 1;
    }
    #note-buttons {
        height: 3;
        align: center middle;
    }
    #btn-note-save {
        margin-right: 2;
    }
    """

    def __init__(self, task_id: str):
        super().__init__()
        self._task_id = task_id

    def compose(self):
        with Vertical(id="note-box"):
            yield Static(
                f"[bold #FF6B35]ADD NOTE: {self._task_id}[/]",
                id="note-title",
            )
            yield TextArea(id="note-input")
            with Horizontal(id="note-buttons"):
                yield Button("Save", variant="success", id="btn-note-save")
                yield Button("Cancel", variant="default", id="btn-note-cancel")

    def on_mount(self):
        try:
            self.query_one("#note-input", TextArea).focus()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-note-save":
            text = self.query_one("#note-input", TextArea).text.strip()
            self.dismiss(text if text else None)
        else:
            self.dismiss(None)
