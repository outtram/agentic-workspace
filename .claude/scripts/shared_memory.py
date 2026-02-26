#!/usr/bin/env python3
"""Shared memory CLI — callable from both Claude Code and OutBot.

Usage:
    python3 .claude/scripts/shared_memory.py write "Hates morning meetings" user_pref
    python3 .claude/scripts/shared_memory.py write "Server IP is 10.0.0.5" fact
    python3 .claude/scripts/shared_memory.py forget "morning meetings"
    python3 .claude/scripts/shared_memory.py search "solar panels"
"""

import sys
from pathlib import Path

# Add brain package to path
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from brain.memory.remember import write_memory, _append_to_section, _append_to_learned
from brain.memory.recall import search_memory, format_recall_context

MEMORY_DIR = str(_project_root / ".claude" / "memory")


def cmd_write(content: str, category: str = "fact") -> str:
    """Write a memory entry to the shared memory files."""
    if category not in ("user_pref", "personality", "fact"):
        category = "fact"
    entry = {"content": content, "category": category}
    saved = write_memory(entry, MEMORY_DIR)
    return f"Saved: {saved} ({category})"


def cmd_forget(search_term: str) -> str:
    """Remove a memory entry by keyword search."""
    from brain.memory.remember import Path as _Path, date, logger

    memory_path = _Path(MEMORY_DIR)
    search = search_term.strip().lower()
    removed = False

    for filepath in [memory_path / "USER.md", memory_path / "LEARNED.md"]:
        if not filepath.exists():
            continue

        lines = filepath.read_text(encoding="utf-8").splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("- ") and search in line.lower():
                print(f"Removed: {line.strip()}")
                removed = True
                continue
            new_lines.append(line)

        if removed:
            filepath.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            break

    return "Memory removed" if removed else "No matching memory found"


def cmd_search(query: str) -> str:
    """Search memory files for matching content."""
    results = search_memory(query, MEMORY_DIR)
    if not results:
        return "No matches found"
    return format_recall_context(results)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]
    if action == "write":
        content = sys.argv[2]
        category = sys.argv[3] if len(sys.argv) > 3 else "fact"
        print(cmd_write(content, category))
    elif action == "forget":
        print(cmd_forget(sys.argv[2]))
    elif action == "search":
        print(cmd_search(sys.argv[2]))
    else:
        print(f"Unknown action: {action}")
        print(__doc__)
        sys.exit(1)
