"""Bottom status strip with shortcut hints and task counts."""
from textual.widgets import Static


_GRID_HINTS = (
    "[bold #FF6B35]Enter[/][dim] Open[/]  "
    "[bold #FF6B35]Space[/][dim] Sel[/]  "
    "[bold #FF6B35]/[/][dim] Cmds[/]  "
    "[bold #FF6B35]t[/][dim] Today[/]  "
    "[bold #FF6B35]d[/][dim] Done[/]  "
    "[bold #FF6B35]e[/][dim] Edit[/]  "
    "[bold #FF6B35][ ][/][dim] Page[/]  "
    "[bold #FF6B35]:[/][dim] Filter[/]  "
    "[bold #FF6B35]?[/][dim] Help[/]"
)

_FOCUS_HINTS = (
    "[bold #FF6B35]\u2191\u2193[/][dim] Fields[/]  "
    "[bold #FF6B35]Enter[/][dim] Edit[/]  "
    "[bold #FF6B35]Esc[/][dim] Back[/]  "
    "[bold #FF6B35]/[/][dim] Cmds[/]  "
    "[bold #FF6B35]t[/][dim] Today[/]  "
    "[bold #FF6B35]d[/][dim] Done[/]  "
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
        voice_active: bool = False,
        voice_recording: bool = False,
        overdue: int = 0,
        telegram_status: str = "",
        view_mode: str = "grid",
        nav_depth: int = 0,
    ):
        # Line 1: context-sensitive hints
        line1 = _FOCUS_HINTS if view_mode == "focus" else _GRID_HINTS

        # Line 2: counts + indicators
        parts = [
            f"{total} tasks",
            f"{today} today",
        ]
        if overdue:
            parts.append(f"[bold red]{overdue} overdue[/]")
        if selected:
            parts.append(f"[#00D4AA]{selected} selected[/]")
        if filter_label:
            parts.append(f"[#FF6B35]filter: {filter_label}[/]")
        if nav_depth:
            parts.append(f"[#FF6B35]depth: {nav_depth}[/]")
        if view_mode == "focus":
            parts.append("[bold #FF6B35]FOCUS[/]")
        if voice_active:
            if voice_recording:
                parts.append("[bold red]voice: RECORDING[/]")
            else:
                parts.append("[bold #FF6B35]voice: ON[/]")
        if telegram_status:
            parts.append(f"[bold #00D4AA]{telegram_status}[/]")
        if view_mode == "grid":
            parts.append(f"Page {page} of {total_pages}")
        line2 = " \u2502 ".join(parts)

        self.update(f"{line1}\n{line2}")
