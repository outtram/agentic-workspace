"""Persist bump state changes to task YAML frontmatter."""
from pathlib import Path

import yaml


def save_stream_state(
    path: Path,
    stream_state: str,
    last_touched: str,
    snoozed_until: str | None = None,
) -> None:
    """Update stream fields in a task file's YAML frontmatter.

    Preserves all existing fields and the markdown body.
    """
    text = path.read_text()
    if not text.startswith("---"):
        return

    parts = text.split("---", 2)
    if len(parts) < 3:
        return

    meta = yaml.safe_load(parts[1])
    if not isinstance(meta, dict):
        return

    meta["stream_state"] = stream_state
    meta["last_touched"] = last_touched
    if snoozed_until is not None:
        meta["snoozed_until"] = snoozed_until
    elif "snoozed_until" in meta:
        del meta["snoozed_until"]

    new_text = f"---\n{yaml.dump(meta, default_flow_style=False, sort_keys=False)}---{parts[2]}"
    path.write_text(new_text)
