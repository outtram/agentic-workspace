"""Verify all 3 help sources are generated from help_data.yml and stay in sync.

This is the most important CC test — it catches the #1 source of bugs:
help text getting out of sync across HELP.md, app.py, and router.py.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CC = ROOT / "brain" / "command_centre"


def _load_help_data():
    """Load the single source of truth."""
    return yaml.safe_load((CC / "help_data.yml").read_text())


def _extract_slash_commands_from_help_md():
    """Extract slash command names from HELP.md."""
    text = (ROOT / "HELP.md").read_text()
    # Match `/command` patterns in backticks within the CC section
    # Find the CC slash commands section
    section = text.split("Command Centre Slash Commands")[1].split("##")[0]
    cmds = set(re.findall(r"`(/[\w-]+)", section))
    # Expand "/q1 .. /q4" shorthand if present
    if "/q1" in cmds and "q4" in section:
        cmds.update(["/q1", "/q2", "/q3", "/q4"])
    return cmds


def _extract_slash_commands_from_router():
    """Extract slash command names from router.py."""
    text = (CC / "router.py").read_text()
    cmds = set()
    # Match cmd == "/xyz" patterns
    cmds.update(re.findall(r'cmd == "(/[\w-]+)"', text))
    # Match cmd in ("/xyz", "/abc") tuple patterns
    for match in re.findall(r'cmd in \(([^)]+)\)', text):
        cmds.update(re.findall(r'"(/[\w-]+)"', match))
    return cmds


def _extract_slash_commands_from_help_data():
    """Extract slash command names from help_data.yml."""
    data = _load_help_data()
    cmds = set()
    for c in data["cc_slash_commands"]:
        # Extract the base command (before any space/args)
        base = c["cmd"].split()[0]
        if ".." in c["cmd"]:
            # "/q1 .. /q4" → /q1, /q2, /q3, /q4
            cmds.update(["/q1", "/q2", "/q3", "/q4"])
        else:
            cmds.add(base)
        # Also add aliases
        for alias in c.get("aliases", []):
            cmds.add(alias)
    return cmds


def _extract_keybindings_from_help_data():
    """Extract all documented keybindings."""
    data = _load_help_data()
    keys = set()
    for section in data["grid_view_keys"].values():
        for k in section:
            keys.add(k["key"])
    for k in data["focus_view_keys"]:
        keys.add(k["key"])
    return keys


# ─── Tests ──────────────────────────────────────────────────────────────────


def test_help_data_exists():
    """help_data.yml must exist as the single source of truth."""
    assert (CC / "help_data.yml").exists(), "help_data.yml missing"


def test_help_data_is_valid_yaml():
    """help_data.yml must parse without errors."""
    data = _load_help_data()
    assert isinstance(data, dict)
    assert "cc_slash_commands" in data
    assert "grid_view_keys" in data


def test_all_router_commands_in_help_data():
    """Every command in router.py should be documented in help_data.yml."""
    router_cmds = _extract_slash_commands_from_router()
    help_cmds = _extract_slash_commands_from_help_data()

    # Commands that are intentional internal redirects (not user-facing docs)
    INTERNAL_REDIRECTS = {"/voice", "/v"}

    router_only = set()
    for cmd in router_cmds:
        if cmd not in help_cmds and cmd not in INTERNAL_REDIRECTS:
            router_only.add(cmd)

    assert not router_only, (
        f"Commands in router.py but not help_data.yml: {router_only}\n"
        "Add them to cc_slash_commands in help_data.yml"
    )


def test_all_help_data_commands_in_router():
    """Every CC command in help_data.yml should be handled in router.py."""
    help_cmds = _extract_slash_commands_from_help_data()
    router_cmds = _extract_slash_commands_from_router()

    help_only = set()
    for cmd in help_cmds:
        if cmd not in router_cmds:
            help_only.add(cmd)

    assert not help_only, (
        f"Commands in help_data.yml but not router.py: {help_only}\n"
        "Either implement the handler or remove from help_data.yml"
    )


def test_help_md_matches_help_data():
    """HELP.md slash commands should match help_data.yml."""
    help_md_cmds = _extract_slash_commands_from_help_md()
    help_data_cmds = _extract_slash_commands_from_help_data()

    # HELP.md may not expand aliases, so only check base commands
    base_data_cmds = set()
    data = _load_help_data()
    for c in data["cc_slash_commands"]:
        base = c["cmd"].split()[0]
        if ".." in c["cmd"]:
            base_data_cmds.update(["/q1", "/q2", "/q3", "/q4"])
        else:
            base_data_cmds.add(base)

    md_only = help_md_cmds - base_data_cmds
    data_only = base_data_cmds - help_md_cmds

    if md_only or data_only:
        msg = ""
        if md_only:
            msg += f"In HELP.md but not help_data.yml: {md_only}\n"
        if data_only:
            msg += f"In help_data.yml but not HELP.md: {data_only}\n"
        msg += "Run: python3 -m brain.command_centre.help_gen"
        assert False, msg


def test_help_gen_check_passes():
    """The help generator's --check mode should report no staleness."""
    import subprocess

    result = subprocess.run(
        ["python3", "-m", "brain.command_centre.help_gen", "--check"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, (
        f"Help outputs are stale:\n{result.stdout}\n"
        "Run: python3 -m brain.command_centre.help_gen"
    )


def test_keybindings_section_not_empty():
    """All keybinding sections should have at least one entry."""
    data = _load_help_data()
    for section_name, keys in data["grid_view_keys"].items():
        assert len(keys) > 0, f"grid_view_keys.{section_name} is empty"
    assert len(data["focus_view_keys"]) > 0
    assert len(data["voice_mode_keys"]) > 0


def test_agents_and_skills_documented():
    """Agents and skills lists should not be empty."""
    data = _load_help_data()
    assert len(data["agents"]) > 0, "No agents documented"
    assert len(data["skills"]) > 0, "No skills documented"
