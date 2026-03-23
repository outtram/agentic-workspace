# AAGLOBAL Copilot Instructions

## Core system shape

AAGLOBAL has three interfaces that share the same file-native state:

- `brain/command_centre/` is the Command Centre TUI. User-facing docs say to launch it with `cc`; the direct Python entrypoint is `python3 -m brain.command_centre`.
- `.claude/agents/`, `.claude/work/`, `.claude/memory/`, and `.claude/skills/` are the Claude Code agent system and its shared state.
- `brain/` is OutBot, the conversational runtime for CLI chat, voice, Telegram, email, heartbeat, and shared workflows.

The important architectural rule is that all three systems read and write the same `.claude/` files. Before changing behaviour, check whether it is implemented in the TUI, an agent workflow, and OutBot separately, or whether it already lives in `brain/workflows/` as shared Python logic.

`docs/ARCHITECTURE.md` is the high-level architecture reference. `.claude/memory/NAVIGATOR.md` is the quickest way to locate work items, memory domains, and agent definitions.

## Commands used in this repo

There is no single “build” command for the repo. CI validates the Python codebase with syntax checks, Ruff, help-sync checks, and pytest.

Run the same checks locally from the repository root:

```bash
# Syntax check all Python under brain/
find brain/ -name "*.py" -exec python3 -m py_compile {} \;

# Lint the main codebase
python3 -m ruff check brain/

# Verify generated help text is in sync
python3 -m brain.command_centre.help_gen --check

# Main Command Centre test suite
python3 -m pytest brain/tests/test_command_centre/ -v

# Full test suite used by CI
python3 -m pytest brain/tests/ -v --ignore=brain/tests/integration
```

Useful single-test patterns:

```bash
# Run one test file
python3 -m pytest brain/tests/test_command_centre/test_help_sync.py -q

# Run one specific test
python3 -m pytest brain/tests/test_command_centre/test_help_sync.py::test_help_gen_check_passes -q

# Run one integration test
python3 -m pytest brain/tests/integration/test_heartbeat_cycle.py::TestHeartbeatCycle::test_due_task_fires_event -q
```

## High-level architecture

The repo is not a conventional app with one entrypoint:

- `README.md` and `docs/ARCHITECTURE.md` describe the system as a shared workspace with Command Centre, Claude Code agents, and OutBot.
- `.claude/work/` stores work items as Markdown with YAML frontmatter. ID ranges matter: PRDs are `OUT-001`+, bugs are `OUT-101`+, tasks are `OUT-201`+.
- `.claude/memory/` stores long-lived memory, including `SOUL.md`, `USER.md`, and YAML domains such as projects, patterns, skills, and decisions.
- `brain/chat.py` is the CLI chat interface. It wires together the database, session manager, memory recall/remember flows, personality loading, email, and daily review workflow.
- `brain/main.py` starts the Telegram bot/orchestrator and heartbeat scheduler.
- `brain/command_centre/router.py` is the command router for the TUI command bar; handlers live under `brain/command_centre/handlers/`.
- `brain/core/claude_client.py` is an important integration point: architecture docs describe it as calling `claude --print`, so this repo is built around the Claude CLI rather than a standalone Anthropic API integration.

## Repo-specific conventions

### Command Centre help is generated, not hand-edited

`brain/command_centre/help_data.yml` is the single source of truth for help text. Do not hand-edit generated help output in `HELP.md`, `brain/command_centre/app.py`, or the `/help` output in `brain/command_centre/router.py`.

When command names or keybindings change:

```bash
python3 -m brain.command_centre.help_gen
```

The pre-commit hook in `.githooks/pre-commit` blocks commits if help output is stale or if Command Centre code changes without related docs staged.

### Structural docs are expected to stay current

If you add or remove major capabilities, agents, skills, or shared-file structures, update:

- `docs/ARCHITECTURE.md` for system shape changes
- `.claude/memory/NAVIGATOR.md` for memory/work-location changes

### Work tracking and memory are file-native

Do not assume a database-backed task system is the source of truth. The main source of truth for work and memory is the `.claude/` directory:

- work items live in `.claude/work/`
- memory lives in `.claude/memory/`
- agent definitions live in `.claude/agents/`
- dashboards and generated artefacts live in `.claude/dashboards/`

Many features only make sense when these files stay aligned across the TUI, Claude Code agents, and OutBot.

### `.claude/reminders/` is a separate package

The reminders sync tooling under `.claude/reminders/` has its own `pyproject.toml`, CLI entrypoint, and test suite. Treat it as a separate Python package rather than as part of the main `brain/` test/lint loop unless your change actually touches that package.

### Follow repository-specific writing and workflow rules

- Use Australian English spelling (`colour`, `organise`, `behaviour`).
- Keep changes concise and evidence-based; this repository’s guidance explicitly prefers verified commands and outputs over assumptions.
- Git hooks are tracked in `.githooks/`, not `.git/hooks/`.
- If you touch `brain/command_centre/`, read `CLAUDE.md` and the pre-commit hook rules before finishing.
