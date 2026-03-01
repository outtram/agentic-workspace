"""Bottom status strip with shortcut hints and task counts."""
from textual.widgets import Static


_HINTS = (
    "[bold #FF6B35]Space[/][dim] Sel[/]  "
    "[bold #FF6B35]a[/][dim] All[/]  "
    "[bold #FF6B35]n[/][dim] None[/]  "
    "[bold #FF6B35]t[/][dim] Today[/]  "
    "[bold #FF6B35]d[/][dim] Done[/]  "
    "[bold #FF6B35]e[/][dim] Edit[/]  "
    "[bold #FF6B35][ ][/][dim] Page[/]  "
    "[bold #FF6B35]/[/][dim] Cmd[/]  "
    "[bold #FF6B35]:[/][dim] Filter[/]  "
    "[bold #FF6B35]?[/][dim] Help[/]"
)


class StatusBarWidget(Static):
    """Two-line status bar — shortcut hints + counts."""

    DEFAULT_CSS = """
    StatusBarWidget {
        height: 2;
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
        filter_label: str = "",
    ):
        # Line 1: shortcut hints
        line1 = _HINTS

        # Line 2: counts
        parts = [
            f"{total} tasks",
            f"{today} today",
        ]
        if selected:
            parts.append(f"[#00D4AA]{selected} selected[/]")
        if filter_label:
            parts.append(f"[#FF6B35]filter: {filter_label}[/]")
        parts.append(f"Page {page} of {total_pages}")
        line2 = " \u2502 ".join(parts)

        self.update(f"{line1}\n{line2}")
