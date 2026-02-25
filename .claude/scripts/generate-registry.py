#!/usr/bin/env python3
"""One-time migration: scan existing OUT-*.md task files and build task-registry.yml."""

import sys
import re
from pathlib import Path
from datetime import datetime, timezone

# Allow imports from .claude/ packages
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from reminders.core.paths import TASK_DIR, WORK_DIR


def extract_frontmatter(filepath: Path) -> dict | None:
    """Parse YAML frontmatter from a markdown file."""
    text = filepath.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.+?)\n---", text, re.DOTALL)
    if not match:
        return None
    return yaml.safe_load(match.group(1))


def build_registry() -> dict:
    """Scan all OUT-*.md files and build the registry dict."""
    entries = {}
    max_id = 0

    task_files = sorted(TASK_DIR.glob("OUT-*.md"))
    print(f"Found {len(task_files)} task files in {TASK_DIR}")

    for filepath in task_files:
        if filepath.name == "template.md":
            continue

        fm = extract_frontmatter(filepath)
        if fm is None:
            print(f"  WARN: no frontmatter in {filepath.name}, skipping")
            continue

        task_id = fm.get("id", "")
        if not task_id:
            print(f"  WARN: no id in {filepath.name}, skipping")
            continue

        # Extract the numeric part for tracking next_id
        id_match = re.match(r"OUT-(\d+)", str(task_id))
        if id_match:
            num = int(id_match.group(1))
            max_id = max(max_id, num)

        # Warn about duplicate IDs (last file wins)
        tid = str(task_id)
        if tid in entries:
            print(f"  WARN: duplicate id {tid} — {entries[tid]['file']} vs {filepath.name} (keeping latter)")

        # Build entry with core fields
        entry = {
            "title": fm.get("title", ""),
            "file": filepath.name,
            "source": fm.get("source", ""),
            "status": fm.get("status", "todo"),
            "created": str(fm.get("created", "")),
        }

        # Only include reminder_id if present
        rid = fm.get("reminder_id")
        if rid:
            entry["reminder_id"] = str(rid)

        entries[tid] = entry

    registry = {
        "schema_version": 1,
        "next_id": max_id + 1,
        "last_synced": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }
    return registry


def main():
    registry = build_registry()
    out_path = WORK_DIR / "task-registry.yml"

    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(
            registry,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    count = len(registry["entries"])
    print(f"\nWrote {count} entries to {out_path}")
    print(f"next_id: {registry['next_id']}")
    print(f"last_synced: {registry['last_synced']}")


if __name__ == "__main__":
    main()
