"""Bottom status strip with task counts."""
from textual.widgets import Static


class StatusBarWidget(Static):
    """Single-line status bar with counts and page info."""

    DEFAULT_CSS = """
    StatusBarWidget {
        height: 1;
        background: #0a0a0a;
        padding: 0 2;
        color: #777777;
    }
    """

    def update_counts(
        self,
        total: int = 0,
        today: int = 0,
        selected: int = 0,
        page: int = 1,
        total_pages: int = 1,
    ):
        parts = [
            f"{total} tasks",
            f"{today} today",
        ]
        if selected:
            parts.append(f"[#00D4AA]{selected} selected[/]")
        parts.append(f"Page {page} of {total_pages}")
        self.update(" \u2502 ".join(parts))
