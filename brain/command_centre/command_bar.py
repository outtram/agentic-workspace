"""Bottom command bar — interactive Input for Phase 2."""
from textual.containers import Horizontal
from textual.widgets import Input, Static


class CommandBarWidget(Horizontal):
    """Command bar with label and interactive text input."""

    DEFAULT_CSS = """
    CommandBarWidget {
        height: 2;
        background: #111111;
        border-top: solid #333333;
    }
    #cmd-label {
        width: auto;
        height: 1;
        padding: 0 1;
        color: #777777;
    }
    #cmd-input {
        width: 1fr;
        height: 1;
        background: #111111;
        border: none;
    }
    #cmd-input:focus {
        border: none;
        background: #222222;
    }
    """

    def compose(self):
        yield Static("\u2318 ", id="cmd-label")
        yield Input(
            placeholder="/ commands  : filter  or type to talk to OutBot",
            id="cmd-input",
        )
