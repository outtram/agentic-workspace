"""Bottom command bar — display only for Phase 1."""
from textual.widgets import Static


class CommandBarWidget(Static):
    """Display-only command bar showing available actions."""

    DEFAULT_CSS = """
    CommandBarWidget {
        height: 3;
        background: #111111;
        padding: 0 2;
        border-top: solid #333333;
    }
    """

    def on_mount(self):
        self.update(
            "\n[dim]\u2318 COMMAND BAR[/]  "
            "[#FF6B35]Space[/] select  "
            "[#FF6B35]t[/] today  "
            r"[#FF6B35]\[\][/] page  "
            "[#FF6B35]1-9[/] jump  "
            "[#FF6B35]Esc\u00d72[/] quit"
        )
