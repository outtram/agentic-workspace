"""Generate all help outputs from the single source of truth: help_data.yml.

Usage:
    python3 -m brain.command_centre.help_gen          # Generate all 3 outputs
    python3 -m brain.command_centre.help_gen --check   # Check if outputs are stale
    python3 -m brain.command_centre.help_gen --dry-run  # Show what would change

Outputs:
    1. HELP.md                          (master help file)
    2. brain/command_centre/app.py      (_HELP_TEXT string — ? overlay)
    3. brain/command_centre/router.py   (/help command output)
"""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    # Inline YAML parser for zero-dependency operation
    yaml = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HELP_DATA = Path(__file__).resolve().parent / "help_data.yml"


def _load_yaml(path: Path) -> dict:
    """Load YAML, falling back to a simple parser if PyYAML unavailable."""
    text = path.read_text()
    if yaml:
        return yaml.safe_load(text)
    # Minimal fallback — only needed if PyYAML not installed
    raise SystemExit("PyYAML required: pip install pyyaml")


def _table(headers: list[str], rows: list[list[str]]) -> str:
    """Build a markdown table."""
    lines = [f"| {' | '.join(headers)} |"]
    lines.append(f"|{'|'.join('-' * (len(h) + 2) for h in headers)}|")
    for row in rows:
        lines.append(f"| {' | '.join(row)} |")
    return "\n".join(lines)


def _key_table(items: list[dict], key_label: str = "Key") -> str:
    """Build a key/action markdown table from a list of dicts."""
    return _table(
        [key_label, "Action"],
        [[f"`{item['key']}`" if 'key' in item else f"`{item['cmd']}`", item.get('action', item.get('desc', ''))] for item in items],
    )


# ---------------------------------------------------------------------------
# Generator 1: HELP.md
# ---------------------------------------------------------------------------

def generate_help_md(data: dict) -> str:
    """Generate the complete HELP.md content."""
    lines = ["# AAGLOBAL Help", ""]

    # Terminal commands
    lines.append("## Terminal Commands (available from anywhere)")
    lines.append("")
    lines.append(_table(
        ["Command", "What it does"],
        [[f"`{c['cmd']}`", c["desc"]] for c in data["terminal_commands"]],
    ))

    # Grid view keybindings
    lines.extend(["", "## Command Centre Keybindings (inside `cc`)", "", "### Grid View (main)", ""])
    for section_name, section_key in [("Navigation", "navigation"), ("Selection", "selection"), ("Actions", "actions")]:
        if section_key == "navigation":
            lines.append(_table(
                ["Key", "Action"],
                [[f"`{k['key']}`" if k['key'] != 'Arrow keys' else k['key'], k['action']] for k in data["grid_view_keys"][section_key]],
            ))
        else:
            for k in data["grid_view_keys"][section_key]:
                pass  # Combined into one table below

    # Actually: produce one combined table for grid view
    lines = lines[:lines.index("### Grid View (main)") + 1]
    lines.append("")
    all_grid_keys = []
    for section in ["navigation", "selection", "actions"]:
        all_grid_keys.extend(data["grid_view_keys"][section])
    lines.append(_table(
        ["Key", "Action"],
        [[k["key"], k["action"]] for k in all_grid_keys],
    ))

    # Focus view
    lines.extend(["", "### Task Focus View (when zoomed into a task)", ""])
    lines.append(_table(
        ["Key", "Action"],
        [[k["key"], k["action"]] for k in data["focus_view_keys"]],
    ))
    lines.append("")
    lines.append("Arrow down past Description to the **Notes & Research** section. Press Enter to view full content.")

    # Diagram view
    if "diagram_view_keys" in data:
        lines.extend(["", "### Diagram View (/diagram)", ""])
        lines.append(_table(
            ["Key", "Action"],
            [[k["key"], k["action"]] for k in data["diagram_view_keys"]],
        ))

    # Filter picker
    lines.extend(["", "### Filter Picker (: key)", ""])
    lines.append(_table(
        ["Key", "Action"],
        [[k["key"], k["action"]] for k in data["filter_picker_keys"]],
    ))

    # Command palette
    lines.extend(["", "### Command Palette (/ key)", ""])
    lines.append(_table(
        ["Key", "Action"],
        [[k["key"], k["action"]] for k in data["command_palette_keys"]],
    ))

    # Voice mode
    lines.extend(["", "### Voice Mode (when active)", ""])
    lines.append(_table(
        ["Key", "Action"],
        [[k["key"], k["action"]] for k in data["voice_mode_keys"]],
    ))

    # CC slash commands
    lines.extend(["", "### Command Centre Slash Commands (inside `cc` command bar)", ""])
    lines.append(_table(
        ["Command", "What it does"],
        [[f"`{c['cmd']}`", c["desc"]] for c in data["cc_slash_commands"]],
    ))

    # Predictions
    lines.extend(["", "### Predictions (on launch)", ""])
    lines.append(data["predictions"]["desc"])

    # Claude Code slash commands
    lines.extend(["", "## Slash Commands (inside Claude Code)", ""])
    lines.append(_table(
        ["Command", "What it does"],
        [[f"`{c['cmd']}`", c["desc"]] for c in data["claude_code_slash_commands"]],
    ))

    # Reminders CLI
    lines.extend(["", "## Reminders CLI (from project root)", ""])
    lines.append(_table(
        ["Command", "What it does"],
        [[f"`{c['cmd']}`", c["desc"]] for c in data["reminders_cli_commands"]],
    ))

    # Agents
    lines.extend(["", "## Agents (available inside Claude Code)", ""])
    lines.append(_table(
        ["Agent", "What it does"],
        [[a["name"], a["desc"]] for a in data["agents"]],
    ))

    # Skills
    lines.extend(["", "## Skills (available inside Claude Code)", ""])
    lines.append(_table(
        ["Skill", "What it does"],
        [[s["name"], s["desc"]] for s in data["skills"]],
    ))

    # Dashboards
    lines.extend(["", "## Dashboards", ""])
    dash_rows = []
    for d in data["dashboards"]:
        loc = d.get("url", f'`{d.get("cmd", "")}`')
        dash_rows.append([loc, d["desc"]])
    lines.append(_table(["URL", "What it shows"], dash_rows))

    # Quick start
    lines.extend([
        "",
        "## Quick Start",
        "",
        "1. `cc` — Command Centre (spatial tile grid)",
        "2. `/daily-review` — full morning review (import, dashboard, priorities)",
        "3. `outbot` — chat with OutBot",
        "",
    ])

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Generator 2: _HELP_TEXT for app.py (Rich markup for TUI overlay)
# ---------------------------------------------------------------------------

def generate_help_text_rich(data: dict) -> str:
    """Generate the Rich-markup _HELP_TEXT string for the ? overlay."""
    lines = [
        '[bold #FF6B35]COMMAND CENTRE — HOTKEYS[/]',
        '[#333333]' + '━' * 34 + '[/]',
        '',
    ]

    # Grid navigation
    lines.append('[bold]Navigation[/]')
    for k in data["grid_view_keys"]["navigation"]:
        lines.append(f'  {k["key"]:<14s}{k["action"]}')

    lines.append('')
    lines.append('[bold]Selection[/]')
    for k in data["grid_view_keys"]["selection"]:
        lines.append(f'  {k["key"]:<14s}{k["action"]}')

    lines.append('')
    lines.append('[bold]Actions[/]')
    for k in data["grid_view_keys"]["actions"]:
        key_display = k["key"]
        # Escape Rich markup characters
        key_display = key_display.replace("[", "\\[").replace("]", "\\]")
        lines.append(f'  {key_display:<14s}{k["action"]}')

    lines.append('')
    lines.append('[bold]Task Focus View[/]  (when zoomed into a task)')
    for k in data["focus_view_keys"]:
        lines.append(f'  {k["key"]:<14s}{k["action"]}')

    if "diagram_view_keys" in data:
        lines.append('')
        lines.append('[bold]Diagram View[/]  (/diagram)')
        for k in data["diagram_view_keys"]:
            lines.append(f'  {k["key"]:<14s}{k["action"]}')

    lines.append('')
    lines.append('[bold]Filter Picker[/]  (: key)')
    for k in data["filter_picker_keys"]:
        lines.append(f'  {k["key"]:<14s}{k["action"]}')

    lines.append('')
    lines.append('[bold]Voice Mode[/]  (when active)')
    for k in data["voice_mode_keys"]:
        lines.append(f'  {k["key"]:<14s}{k["action"]}')

    lines.append('')
    lines.append('[bold]Quit[/]')
    lines.append('  Escape        Back through levels → double-tap to quit')
    lines.append('')
    lines.append('[dim]Press any key to close[/]')

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generator 3: /help command output for router.py (Rich markup)
# ---------------------------------------------------------------------------

def generate_help_router(data: dict) -> str:
    """Generate the Rich-markup string for the /help slash command."""
    lines = [
        '[bold]Navigation[/]',
        '  Enter       Drill into children / open Focus View',
        '  Space       Toggle select',
        '  Escape      Back one level / clear / quit',
        '  /           Command Palette (agents, skills, commands)',
        '',
        '[bold]Slash Commands[/]',
    ]
    for c in data["cc_slash_commands"]:
        cmd = c["cmd"]
        # Pad and format
        cmd_display = cmd.split(" ")[0]  # Just the command, no args
        if ".." in cmd:
            cmd_display = cmd  # Keep "/q1 .. /q4" as-is
        lines.append(f'  {cmd_display:<14s}{c["desc"]}')

    lines.extend([
        '',
        '[bold]Filters[/]  (: opens Filter Picker)',
        '  :q1 :q2 :q3 :q4   Filter by quadrant',
        '  :overdue          Overdue tasks',
        '  :today            Today list',
        '  :search term      Text search',
        '',
        '[bold]Focus View[/]',
        '  ↑ ↓          Navigate fields',
        '  Enter       Edit field / cycle choice',
        '  Escape      Back to grid',
        '  /           Commands for this task',
        '',
        '[dim]Or just type to talk to OutBot[/]',
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Patch files
# ---------------------------------------------------------------------------

def _patch_app_py(help_text: str, dry_run: bool = False) -> bool:
    """Replace _HELP_TEXT in app.py. Returns True if changed."""
    app_path = PROJECT_ROOT / "brain" / "command_centre" / "app.py"
    content = app_path.read_text()

    # Match the _HELP_TEXT = """...""" block
    pattern = r'_HELP_TEXT = """\\\n.*?"""'
    replacement = f'_HELP_TEXT = """\\\n{help_text}"""'

    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    if new_content == content:
        return False
    if not dry_run:
        app_path.write_text(new_content)
    return True



def _write_help_md(help_md: str, dry_run: bool = False) -> bool:
    """Write HELP.md. Returns True if changed."""
    help_path = PROJECT_ROOT / "HELP.md"
    existing = help_path.read_text() if help_path.exists() else ""
    if existing == help_md:
        return False
    if not dry_run:
        help_path.write_text(help_md)
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    check_mode = "--check" in sys.argv
    dry_run = "--dry-run" in sys.argv

    data = _load_yaml(HELP_DATA)

    help_md = generate_help_md(data)
    help_rich = generate_help_text_rich(data)

    if check_mode:
        # Check if any output is stale
        # Note: router.py reads help_data.yml at runtime — no patching needed.
        stale = []
        if _write_help_md(help_md, dry_run=True):
            stale.append("HELP.md")
        if _patch_app_py(help_rich, dry_run=True):
            stale.append("app.py (_HELP_TEXT)")

        if stale:
            print(f"STALE: {', '.join(stale)}")
            print("Run: python3 -m brain.command_centre.help_gen")
            sys.exit(1)
        else:
            print("OK: All help outputs are up to date.")
            sys.exit(0)

    # Generate
    # Note: router.py reads help_data.yml at runtime — no patching needed.
    changes = []
    if _write_help_md(help_md, dry_run):
        changes.append("HELP.md")
    if _patch_app_py(help_rich, dry_run):
        changes.append("app.py (_HELP_TEXT)")

    if changes:
        verb = "Would update" if dry_run else "Updated"
        print(f"{verb}: {', '.join(changes)}")
    else:
        print("No changes needed — all outputs are up to date.")


if __name__ == "__main__":
    main()
