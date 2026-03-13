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
    import glob
    common_patterns = [
        str(Path.home() / ".cabal" / "share" / "tidal-*" / "BootTidal.hs"),
        str(Path.home() / ".local" / "state" / "cabal" / "store" / "*" / "tdl-*" / "share" / "BootTidal.hs"),
        str(Path.home() / ".local" / "state" / "cabal" / "store" / "*" / "*tidal*" / "share" / "BootTidal.hs"),
        "/usr/local/share/tidal/BootTidal.hs",
        "/opt/homebrew/share/tidal/BootTidal.hs",
    ]
    for pattern in common_patterns:
        matches = glob.glob(pattern)
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
            await self._send_raw(f":script {boot}")
            # Wait for boot to complete
            await asyncio.sleep(3)
            # Set initial BPM
            await self._send_raw(f"setcps ({self._bpm}/60.0/4.0)")
            return True
        except Exception:
            self._process = None
            return False

    async def send(self, code: str):
        """Send Tidal code to GHCi. Splits into individual statements."""
        if not self.is_running():
            return
        # Split code into individual statements (dX blocks, setcps, hush, etc.)
        statements = self._split_statements(code)
        for stmt in statements:
            lines = [ln for ln in stmt.splitlines() if ln.strip()]
            if not lines:
                continue
            for line in lines:
                self._track_pattern(line)
            if len(lines) > 1:
                await self._send_raw(":{")
                for line in lines:
                    await self._send_raw(line)
                await self._send_raw(":}")
            else:
                await self._send_raw(lines[0])

    @staticmethod
    def _split_statements(code: str) -> list[str]:
        """Split a code block into individual Tidal statements.

        Each dX $, setcps, hush etc. is a separate statement.
        Multi-line dX blocks (with continuation via # or $) stay grouped.
        Comment-only lines are stripped.
        """
        statements: list[str] = []
        current: list[str] = []

        for line in code.splitlines():
            stripped = line.strip()
            # Skip empty lines and comments
            if not stripped or stripped.startswith("--"):
                continue
            # New statement starts with dX $, setcps, hush, once, etc.
            if re.match(r"(d\d{1,2}\s*\$|setcps|hush|once|xfade)", stripped):
                if current:
                    statements.append("\n".join(current))
                current = [stripped]
            elif current:
                # Continuation line (indented or starts with #, $, etc.)
                current.append(stripped)
            else:
                # Standalone line
                statements.append(stripped)

        if current:
            statements.append("\n".join(current))

        return statements

    async def hush(self):
        """Silence all patterns."""
        self._active_patterns.clear()
        await self._send_raw("hush")

    async def set_bpm(self, bpm: int):
        """Set the tempo in BPM."""
        self._bpm = bpm
        await self._send_raw(f"setcps ({bpm}/60.0/4.0)")

    def get_active_patterns(self) -> dict[str, str]:
        """Return dict of active pattern slots (d1-d16) to their code."""
        return dict(self._active_patterns)

    def is_running(self) -> bool:
        """Check if GHCi process is alive."""
        return self._process is not None and self._process.returncode is None

    async def stop(self):
        """Kill the GHCi subprocess."""
        if self._process and self._process.returncode is None:
            await self._send_raw(":quit")
            try:
                await asyncio.wait_for(self._process.wait(), timeout=3)
            except asyncio.TimeoutError:
                self._process.kill()
        self._process = None
        self._active_patterns.clear()

    async def _send_raw(self, text: str):
        """Write raw text to GHCi stdin and flush."""
        if self._process and self._process.stdin:
            try:
                self._process.stdin.write(f"{text}\n".encode())
                await self._process.stdin.drain()
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
