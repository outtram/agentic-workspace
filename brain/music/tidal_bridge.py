"""TidalCycles bridge — manages a GHCi subprocess with Tidal loaded.

Sends pattern code to GHCi's stdin and tracks active patterns.
"""
from __future__ import annotations

import asyncio
import re
import shutil
from pathlib import Path


def _find_boot_tidal() -> str | None:
    """Locate BootTidal.hs on the system."""
    common_paths = [
        Path.home() / ".cabal" / "share" / "tidal-*" / "BootTidal.hs",
        Path("/usr/local/share/tidal/BootTidal.hs"),
        Path("/opt/homebrew/share/tidal/BootTidal.hs"),
    ]
    import glob
    for pattern in common_paths:
        matches = glob.glob(str(pattern))
        if matches:
            return sorted(matches)[-1]  # Latest version
    return None


class TidalBridge:
    """Manages a GHCi process with TidalCycles loaded."""

    def __init__(self):
        self._process: asyncio.subprocess.Process | None = None
        self._active_patterns: dict[str, str] = {}
        self._bpm: int = 128

    async def start(self) -> bool:
        """Launch GHCi with TidalCycles. Returns True on success."""
        if self._process and self._process.returncode is None:
            return True  # Already running

        ghci = shutil.which("ghci")
        if not ghci:
            return False

        boot = _find_boot_tidal()
        if not boot:
            return False

        try:
            self._process = await asyncio.create_subprocess_exec(
                ghci,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            # Boot TidalCycles
            self._send_raw(f":script {boot}")
            # Wait a moment for boot
            await asyncio.sleep(2)
            # Set initial BPM
            self._send_raw(f"setcps ({self._bpm}/60/4)")
            return True
        except Exception:
            self._process = None
            return False

    def send(self, code: str):
        """Send a line of Tidal code to GHCi."""
        if not self.is_running():
            return
        # Track pattern assignment
        self._track_pattern(code)
        self._send_raw(code)

    def hush(self):
        """Silence all patterns."""
        self._active_patterns.clear()
        self._send_raw("hush")

    def set_bpm(self, bpm: int):
        """Set the tempo in BPM."""
        self._bpm = bpm
        self._send_raw(f"setcps ({bpm}/60/4)")

    def get_active_patterns(self) -> dict[str, str]:
        """Return dict of active pattern slots (d1-d16) to their code."""
        return dict(self._active_patterns)

    def is_running(self) -> bool:
        """Check if GHCi process is alive."""
        return self._process is not None and self._process.returncode is None

    async def stop(self):
        """Kill the GHCi subprocess."""
        if self._process and self._process.returncode is None:
            self._send_raw(":quit")
            try:
                await asyncio.wait_for(self._process.wait(), timeout=3)
            except asyncio.TimeoutError:
                self._process.kill()
        self._process = None
        self._active_patterns.clear()

    def _send_raw(self, text: str):
        """Write raw text to GHCi stdin."""
        if self._process and self._process.stdin:
            try:
                self._process.stdin.write(f"{text}\n".encode())
            except Exception:
                pass

    def _track_pattern(self, code: str):
        """Parse a Tidal code line and track which slot it uses."""
        match = re.match(r"(d\d{1,2})\s*\$", code.strip())
        if match:
            slot = match.group(1)
            self._active_patterns[slot] = code.strip()
        # Check for silence command on a slot
        silence_match = re.match(r"(d\d{1,2})\s+silence", code.strip())
        if silence_match:
            slot = silence_match.group(1)
            self._active_patterns.pop(slot, None)
