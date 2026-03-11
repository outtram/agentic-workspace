"""Music mode view — TidalCycles natural language interface.

Lazy-loaded: only imported when user enters music mode via 'm' key.
Three-panel layout: pattern monitor, active patterns sidebar, chat input.
"""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Input, Static

if TYPE_CHECKING:
    pass

MUSIC_DIR = Path(__file__).resolve().parent.parent / "music"


def _tidal_available() -> bool:
    """Check if TidalCycles (ghci) is on the PATH."""
    import shutil
    return shutil.which("ghci") is not None


class PatternMonitor(VerticalScroll):
    """Shows the live Tidal code for the current session."""

    DEFAULT_CSS = """
    PatternMonitor {
        width: 3fr;
        background: #0a0a0a;
        border: solid #333333;
        padding: 1 2;
    }
    """

    def compose(self):
        yield Static(
            "[bold #FF6B35]PATTERN MONITOR[/]\n"
            "[dim]Patterns you create will appear here[/]",
            id="pattern-display",
        )

    def update_patterns(self, history: list[dict]):
        """Update displayed pattern history."""
        try:
            display = self.query_one("#pattern-display", Static)
        except Exception:
            return

        if not history:
            display.update(
                "[bold #FF6B35]PATTERN MONITOR[/]\n"
                "[dim]Patterns you create will appear here[/]"
            )
            return

        lines = ["[bold #FF6B35]PATTERN MONITOR[/]", ""]
        for entry in history[-20:]:  # Show last 20 entries
            request = entry.get("request", "")
            code = entry.get("code", "")
            status = entry.get("status", "sent")
            if status == "sent":
                colour = "#00D4AA"
                icon = "▶"
            elif status == "pending":
                colour = "#d4aa00"
                icon = "…"
            else:
                colour = "#FF6B35"
                icon = "✗"
            lines.append(f"[dim]> {request}[/]")
            lines.append(f"[{colour}]{icon}[/] [bold]{code}[/]")
            lines.append("")

        display.update("\n".join(lines))


class ActivePatterns(Static):
    """Sidebar showing which patterns (d1-d16) are active."""

    DEFAULT_CSS = """
    ActivePatterns {
        width: 1fr;
        min-width: 24;
        background: #111111;
        border-left: solid #333333;
        padding: 1 2;
    }
    """

    def update_active(self, patterns: dict[str, str], bpm: int = 128,
                      key: str = "C", song_name: str = ""):
        """Update the active patterns display."""
        lines = ["[bold #FF6B35]ACTIVE[/]", ""]
        if song_name:
            lines.append(f"[bold]{song_name}[/]")
        lines.append(f"[#00D4AA]{bpm} BPM[/] | [#00D4AA]{key}[/]")
        lines.append("")

        for slot in [f"d{i}" for i in range(1, 17)]:
            code = patterns.get(slot)
            if code:
                # Truncate long patterns
                display_code = code if len(code) < 40 else code[:37] + "..."
                lines.append(f"[bold #00D4AA]{slot}[/]: {display_code}")
            else:
                lines.append(f"[dim]{slot}: (silent)[/]")

        self.update("\n".join(lines))


class MusicChatInput(Container):
    """Bottom chat bar for natural language music commands."""

    DEFAULT_CSS = """
    MusicChatInput {
        height: auto;
        max-height: 8;
        background: #0a0a0a;
        border-top: solid #FF6B35;
        padding: 0 1;
    }
    #music-status {
        height: 1;
        padding: 0 1;
        color: #777777;
    }
    #music-input {
        background: #111111;
        border: none;
        color: #ffffff;
    }
    #music-preview {
        height: auto;
        max-height: 4;
        padding: 0 1;
        color: #d4aa00;
        display: none;
    }
    """

    def compose(self):
        yield Static(
            "[dim]Describe what you want to hear...[/]",
            id="music-status",
        )
        yield Static("", id="music-preview")
        yield Input(
            placeholder="e.g. 'give me a 4 on the floor house beat'",
            id="music-input",
        )

    def show_preview(self, code: str):
        """Show generated code for confirmation."""
        try:
            preview = self.query_one("#music-preview", Static)
            status = self.query_one("#music-status", Static)
            preview.update(
                f"[bold #d4aa00]Generated:[/] {code}\n"
                "[dim][Enter] send  [e] edit  [x] cancel[/]"
            )
            preview.styles.display = "block"
            status.update("[bold #d4aa00]Review code below...[/]")
        except Exception:
            pass

    def clear_preview(self):
        """Hide the preview bar."""
        try:
            preview = self.query_one("#music-preview", Static)
            status = self.query_one("#music-status", Static)
            preview.update("")
            preview.styles.display = "none"
            status.update("[dim]Describe what you want to hear...[/]")
        except Exception:
            pass

    def set_status(self, text: str):
        """Update the status line."""
        try:
            status = self.query_one("#music-status", Static)
            status.update(text)
        except Exception:
            pass


class MusicView(Container):
    """Main music mode container — pattern monitor + active patterns + chat."""

    DEFAULT_CSS = """
    MusicView {
        display: none;
        width: 3fr;
    }
    #music-panels {
        height: 1fr;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._bridge = None
        self._translator = None
        self._song_manager = None
        self._current_song: dict | None = None
        self._history: list[dict] = []
        self._pending_code: str | None = None
        self._active_patterns: dict[str, str] = {}
        self._bpm: int = 128
        self._key: str = "C"
        self._genre: str = ""

    def compose(self):
        with Vertical():
            with Horizontal(id="music-panels"):
                yield PatternMonitor()
                yield ActivePatterns()
            yield MusicChatInput()

    def _ensure_modules(self):
        """Lazy-load music modules on first use."""
        if self._song_manager is None:
            from brain.music.song_manager import SongManager
            self._song_manager = SongManager()
        if self._translator is None:
            from brain.music.translator import TidalTranslator
            self._translator = TidalTranslator()
        if self._bridge is None and _tidal_available():
            from brain.music.tidal_bridge import TidalBridge
            self._bridge = TidalBridge()

    def activate(self):
        """Called when entering music mode."""
        self._ensure_modules()
        if self._current_song is None and self._song_manager:
            self._current_song = self._song_manager.create_song(
                bpm=self._bpm, key=self._key, genre=self._genre
            )
        self._refresh_display()
        # Focus the input
        try:
            inp = self.query_one("#music-input", Input)
            inp.focus()
        except Exception:
            pass

    def deactivate(self):
        """Called when leaving music mode."""
        pass  # Keep state alive for when user returns

    @property
    def song_name(self) -> str:
        if self._current_song:
            return f"MUS-{self._current_song.get('id', '???')}-{self._current_song.get('name', '???')}"
        return ""

    @property
    def status_info(self) -> dict:
        """Return info for the status bar."""
        return {
            "song": self.song_name,
            "bpm": self._bpm,
            "key": self._key,
            "playing": self._bridge.is_running() if self._bridge else False,
            "pattern_count": len(self._active_patterns),
        }

    def _refresh_display(self):
        """Update all sub-widgets."""
        try:
            monitor = self.query_one(PatternMonitor)
            monitor.update_patterns(self._history)
        except Exception:
            pass
        try:
            sidebar = self.query_one(ActivePatterns)
            sidebar.update_active(
                self._active_patterns,
                bpm=self._bpm,
                key=self._key,
                song_name=self.song_name,
            )
        except Exception:
            pass

    async def handle_input(self, text: str) -> str | None:
        """Process natural language input from the chat bar."""
        text = text.strip()
        if not text:
            return None

        # Special commands
        if text.lower() == "hush":
            return self._do_hush()

        self._ensure_modules()

        # Translate natural language to Tidal code
        if self._translator is None:
            return "[red]Translator not available — check Claude API config[/]"

        try:
            chat_input = self.query_one(MusicChatInput)
            chat_input.set_status("[dim]Translating...[/]")
        except Exception:
            pass

        context = {
            "active_patterns": self._active_patterns,
            "bpm": self._bpm,
            "key": self._key,
            "genre": self._genre,
        }

        try:
            code = await self._translator.translate(text, context)
        except Exception as e:
            return f"[red]Translation error: {e}[/]"

        # Show preview for confirmation
        self._pending_code = code
        self._history.append({
            "request": text,
            "code": code,
            "status": "pending",
        })
        self._refresh_display()

        try:
            chat_input = self.query_one(MusicChatInput)
            chat_input.show_preview(code)
        except Exception:
            pass

        return None  # Waiting for confirm/edit/cancel

    def confirm_code(self):
        """Send pending code to TidalCycles."""
        if not self._pending_code:
            return

        code = self._pending_code
        self._pending_code = None

        # Track the pattern assignment
        self._track_pattern(code)

        # Send to bridge if available
        if self._bridge and self._bridge.is_running():
            self._bridge.send(code)

        # Update history
        if self._history:
            self._history[-1]["status"] = "sent"

        # Save to session file
        if self._current_song and self._song_manager:
            song_id = self._current_song.get("id", "")
            self._song_manager.append_session(song_id, code)

        try:
            chat_input = self.query_one(MusicChatInput)
            chat_input.clear_preview()
        except Exception:
            pass

        self._refresh_display()

    def cancel_code(self):
        """Cancel pending code."""
        self._pending_code = None
        if self._history:
            self._history[-1]["status"] = "cancelled"
        try:
            chat_input = self.query_one(MusicChatInput)
            chat_input.clear_preview()
        except Exception:
            pass
        self._refresh_display()

    def get_pending_code(self) -> str | None:
        """Return pending code for editing."""
        return self._pending_code

    def set_edited_code(self, code: str):
        """Update the pending code after editing."""
        self._pending_code = code
        if self._history:
            self._history[-1]["code"] = code
        try:
            chat_input = self.query_one(MusicChatInput)
            chat_input.show_preview(code)
        except Exception:
            pass
        self._refresh_display()

    def _track_pattern(self, code: str):
        """Parse a Tidal code line and track which pattern slot it uses."""
        import re
        match = re.match(r"(d\d{1,2})\s*\$", code.strip())
        if match:
            slot = match.group(1)
            self._active_patterns[slot] = code.strip()

    def _do_hush(self) -> str:
        """Silence all patterns."""
        self._active_patterns.clear()
        if self._bridge and self._bridge.is_running():
            self._bridge.hush()
        self._history.append({
            "request": "hush",
            "code": "hush",
            "status": "sent",
        })
        self._refresh_display()
        return "[#FF6B35]Hushed — all patterns silenced[/]"

    def new_song(self):
        """Create a new song."""
        self._ensure_modules()
        if self._song_manager:
            self._current_song = self._song_manager.create_song(
                bpm=self._bpm, key=self._key, genre=self._genre
            )
            self._active_patterns.clear()
            self._history.clear()
            self._pending_code = None
            self._refresh_display()

    def adjust_bpm(self, delta: int):
        """Adjust BPM by delta."""
        self._bpm = max(40, min(300, self._bpm + delta))
        if self._bridge and self._bridge.is_running():
            self._bridge.set_bpm(self._bpm)
        if self._current_song:
            self._current_song["bpm"] = self._bpm
        self._refresh_display()

    def save_session(self):
        """Save current session to song folder."""
        if self._current_song and self._song_manager:
            song_id = self._current_song.get("id", "")
            # Save all active patterns
            code_lines = []
            for slot, code in sorted(self._active_patterns.items()):
                code_lines.append(code)
            self._song_manager.save_session(song_id, "\n".join(code_lines))
            self._song_manager.update_metadata(
                song_id,
                bpm=self._bpm,
                key=self._key,
                genre=self._genre,
                patterns_used=list(self._active_patterns.keys()),
            )
            return True
        return False

    def open_visualiser(self):
        """Launch the Chrome visualiser."""
        html_path = MUSIC_DIR / "visualiser" / "index.html"
        if not html_path.exists():
            return False
        params = f"?song={self.song_name}&bpm={self._bpm}&key={self._key}"
        url = f"file://{html_path}{params}"
        subprocess.Popen(["open", "-a", "Google Chrome", url])
        return True
