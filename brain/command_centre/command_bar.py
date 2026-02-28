"""Bottom command bar — interactive Input for Phase 2."""
from textual.containers import Horizontal
from textual.widgets import Input, Static


class CommandBarWidget(Horizontal):
    """Command bar with label and interactive text input."""

    DEFAULT_CSS = """
    CommandBarWidget {
        height: 3;
        background: #111111;
        border-top: solid #333333;
    }
    #cmd-label {
        width: auto;
        padding: 1 1;
        color: #777777;
    }
    #cmd-input {
        width: 1fr;
        background: #111111;
        border: none;
        padding: 1 0;
    }
    #cmd-input:focus {
        border: tall #FF6B35;
    }
    """

    def compose(self):
        yield Static("\u2318 ", id="cmd-label")
        yield Input(
            placeholder="/ commands  : filter  or type to talk to OutBot",
            id="cmd-input",
        )
