"""Handle /remember and /forget slash commands."""

import subprocess
import sys
from pathlib import Path

from brain.command_centre import PROJECT_ROOT

MEMORY_DIR = str(PROJECT_ROOT / ".claude" / "memory")
SHARED_MEMORY_SCRIPT = str(PROJECT_ROOT / ".claude" / "scripts" / "shared_memory.py")


async def handle_remember(text: str, claude_client) -> str:
    """Save a memory (shared with OutBot).

    Uses Claude to extract what to remember and classify it,
    then writes to both local memory files and shared memory.
    """
    if not text.strip():
        return (
            "[bold]Usage:[/] /remember <thing to remember>\n"
            "Example: /remember Troy hates morning meetings"
        )

    try:
        from brain.memory.remember import extract_memory, write_memory
    except ImportError:
        return "[red]Memory module not available[/]"

    # Extract and classify via Claude
    entry = await extract_memory(text, claude_client)
    result = write_memory(entry, MEMORY_DIR)

    # Also write to shared memory so OutBot sees it
    try:
        subprocess.run(
            [sys.executable, SHARED_MEMORY_SCRIPT, "write", entry["content"], entry["category"]],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass  # Shared memory is best-effort

    return f"[#00D4AA]Remembered:[/] {result}"


async def handle_forget(text: str, claude_client) -> str:
    """Remove a stored memory.

    Uses Claude to extract the search term, then removes matching
    entries from both local memory files and shared memory.
    """
    if not text.strip():
        return (
            "[bold]Usage:[/] /forget <thing to forget>\n"
            "Example: /forget morning meetings"
        )

    try:
        from brain.memory.remember import forget_memory
    except ImportError:
        return "[red]Memory module not available[/]"

    removed = await forget_memory(text, MEMORY_DIR, claude_client)

    if removed:
        # Also remove from shared memory
        try:
            subprocess.run(
                [sys.executable, SHARED_MEMORY_SCRIPT, "forget", text],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass
        return f"[#00D4AA]Forgotten:[/] {text}"
    else:
        return f"[yellow]No matching memory found for:[/] {text}"
