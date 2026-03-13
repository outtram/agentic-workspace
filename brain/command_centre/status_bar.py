"""Bottom status strip with shortcut hints and task counts."""
from textual.widgets import Static


_GRID_HINTS = (
    "[bold #FF6B35]Enter[/][dim] Open[/]  "
    "[bold #FF6B35]Space[/][dim] Sel[/]  "
    "[bold #FF6B35]/[/][dim] Cmds[/]  "
    "[bold #FF6B35]c[/][dim] Chat[/]  "
    "[bold #FF6B35]t[/][dim] Today[/]  "
    "[bold #FF6B35]d[/][dim] Done[/]  "
    "[bold #FF6B35]e[/][dim] Edit[/]  "
    "[bold #FF6B35]v[/][dim] View[/]  "
    "[bold #FF6B35]m[/][dim] Music[/]  "
    "[bold #FF6B35][ ][/][dim] Page[/]  "
    "[bold #FF6B35]:[/][dim] Filter[/]  "
    "[bold #FF6B35]?[/][dim] Help[/]"
)

_FOCUS_HINTS = (
    "[bold #FF6B35]\u2191\u2193[/][dim] Fields[/]  "
    "[bold #FF6B35]Enter[/][dim] Edit[/]  "
    "[bold #FF6B35]Esc[/][dim] Back[/]  "
    "[bold #FF6B35]/[/][dim] Cmds[/]  "
    "[bold #FF6B35]c[/][dim] Chat[/]  "
    "[bold #FF6B35]t[/][dim] Today[/]  "
    "[bold #FF6B35]d[/][dim] Done[/]  "
    "[bold #FF6B35]?[/][dim] Help[/]"
)

_DIAGRAM_HINTS = (
    "[bold #FF6B35]Arrows[/][dim] Move[/]  "
    "[bold #FF6B35]Enter[/][dim] Drill[/]  "
    "[bold #FF6B35]Esc[/][dim] Back[/]  "
    "[bold #FF6B35]1-9[/][dim] Jump[/]  "
    "[bold #FF6B35]v[/][dim] View[/]  "
    "[bold #FF6B35]m[/][dim] Music[/]  "
    "[bold #FF6B35]/[/][dim] Cmds[/]  "
    "[bold #FF6B35]c[/][dim] Chat[/]  "
    "[bold #FF6B35]?[/][dim] Help[/]"
)

_STREAM_HINTS = (
    "[bold #FF6B35]Enter[/][dim] Open[/]  "
    "[bold #FF6B35]t[/][dim] Top[/]  "
    "[bold #FF6B35]b[/][dim] Back[/]  "
    "[bold #FF6B35]s[/][dim] Snooze[/]  "
    "[bold #FF6B35]d[/][dim] Done[/]  "
    "[bold #FF6B35]z[/][dim] Undo[/]  "
    "[bold #FF6B35]v[/][dim] View[/]  "
    "[bold #FF6B35]m[/][dim] Music[/]  "
    "[bold #FF6B35]c[/][dim] Chat[/]  "
    "[bold #FF6B35]/[/][dim] Cmds[/]  "
    "[bold #FF6B35]:[/][dim] Filter[/]  "
    "[bold #FF6B35]?[/][dim] Help[/]"
)


_MUSIC_HINTS = (
    "[bold #FF6B35]Enter[/][dim] Send[/]  "
    "[bold #FF6B35]v[/][dim] Visualiser[/]  "
    "[bold #FF6B35]s[/][dim] Save[/]  "
    "[bold #FF6B35]h[/][dim] Hush[/]  "
    "[bold #FF6B35]n[/][dim] New Song[/]  "
    "[bold #FF6B35]+/-[/][dim] BPM[/]  "
    "[bold #FF6B35]Esc[/][dim] Exit[/]  "
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
        heartbeat_status: str = "",
        view_mode: str = "grid",
        nav_depth: int = 0,
        diagram_title: str = "",
        diagram_depth: int = 0,
        diagram_node_count: int = 0,
        stream_new: int = 0,
        stream_back: int = 0,
        stream_snoozed: int = 0,
        music_song: str = "",
        music_bpm: int = 128,
        music_key: str = "C",
        music_playing: bool = False,
        music_patterns: int = 0,
    ):
        # Line 1: context-sensitive hints
        if view_mode == "music":
            line1 = _MUSIC_HINTS
        elif view_mode == "diagram":
            line1 = _DIAGRAM_HINTS
        elif view_mode == "focus":
            line1 = _FOCUS_HINTS
        else:
            line1 = _GRID_HINTS

        # Music mode — custom line 2
        if view_mode == "music":
            play_icon = "\u25b6" if music_playing else "\u25a0"
            parts = [f"[bold #FF6B35]\u266a MUSIC[/]"]
            if music_song:
                parts.append(f"[bold]{music_song}[/]")
            parts.append(f"[#00D4AA]{music_bpm} BPM[/]")
            parts.append(f"[#00D4AA]{music_key}[/]")
            if music_patterns:
                parts.append(f"{music_patterns} patterns")
            parts.append(f"{play_icon}")
            line2 = " \u2502 ".join(parts)
            self.update(f"{line1}\n{line2}")
            return

        # Diagram mode — custom line 2
        if view_mode == "diagram":
            parts = [f"[bold #FF6B35]DIAGRAM[/]"]
            if diagram_title:
                parts.append(diagram_title)
            parts.append(f"{diagram_node_count} nodes")
            if diagram_depth:
                parts.append(f"[#FF6B35]depth: {diagram_depth}[/]")
            line2 = " \u2502 ".join(parts)
            self.update(f"{line1}\n{line2}")
            return

        # Stream mode — custom line 2
        if view_mode == "stream":
            line1 = _STREAM_HINTS
            parts = [f"{total} items"]
            if stream_new:
                parts.append(f"[#00D4AA]{stream_new} new[/]")
            if stream_back:
                parts.append(f"[dim]{stream_back} back[/]")
            if stream_snoozed:
                parts.append(f"[#d4aa00]{stream_snoozed} snoozed[/]")
            if telegram_status:
                parts.append(f"[bold #00D4AA]{telegram_status}[/]")
            if heartbeat_status:
                parts.append(f"[bold #FF6B35]{heartbeat_status}[/]")
            parts.append("Stream View")
            line2 = " \u2502 ".join(parts)
            self.update(f"{line1}\n{line2}")
            return

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
        if heartbeat_status:
            parts.append(f"[bold #00D4AA]{heartbeat_status}[/]")
        if view_mode == "grid":
            parts.append(f"Page {page} of {total_pages}")
        line2 = " \u2502 ".join(parts)

        self.update(f"{line1}\n{line2}")
