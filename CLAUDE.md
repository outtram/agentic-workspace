# CLAUDE.md

## Project: AAGLOBAL
> Troy Outtram's agentic development environment

## Troy's Preferences (IMPORTANT)
- **ADHD + Dyslexia:** Keep responses short, structured, actionable
- **Australian English** spelling (colour, organise, behaviour)
- **Confirm before executing** changes
- **CLI tools preferred** (gh, git) over MCP where possible
- **YAGNI principle:** Build simplest thing that works
- **Evidence over claims:** Verify before declaring success

## Memory System
File-native memory at `.claude/memory/`. Quick grep patterns:
```bash
grep "status: active" .claude/memory/projects/*.yml     # Active projects
grep -l "status: draft\|open\|todo" .claude/work/*/*.md  # Open work items
grep -l "priority: high\|critical" .claude/work/*/*.md   # High priority
```

## Repository Strategy
- **Branching:** main (prod), dev (staging), feature/OUT-XX-description
- **Commits:** Prefix with work item ID: `OUT-XX: description`
- **Work Tracking:** File-based at `.claude/work/` (tasks/bugs/prd)

## Command Centre — Single Source of Truth (CRITICAL)
**All help text is generated from one file: `brain/command_centre/help_data.yml`**

When modifying Command Centre files:
1. Edit `help_data.yml` if commands/keys changed
2. Run: `python3 -m brain.command_centre.help_gen`
3. Stage the updated outputs (HELP.md, app.py)
4. The pre-commit hook will block if outputs are stale

**IMPORTANT:** Do NOT manually edit the help text in `app.py` (`_HELP_TEXT`) or `HELP.md`. Edit `help_data.yml` and regenerate.

## Pre-Commit Checklist (MANDATORY)
Before running `git commit`, verify ALL of these:
1. **Syntax check:** `python3 -m py_compile` on every changed .py file
2. **Tests pass:** `python3 -m pytest brain/tests/test_command_centre/ -x -q`
3. **Help sync:** `python3 -m brain.command_centre.help_gen --check`
4. **Architecture:** If new feature added, update `docs/ARCHITECTURE.md`
5. **NAVIGATOR:** If memory structure changed, update `.claude/memory/NAVIGATOR.md`
6. **Australian English:** colour, organise, behaviour (not US spelling)

## Shared Memory (OutBot + Claude Code)
When Troy says "remember X" or "don't forget X":
```bash
python3 .claude/scripts/shared_memory.py write "content here" user_pref|personality|fact
python3 .claude/scripts/shared_memory.py forget "search term"
```

## Workflow Commands
- `/using-superpowers` — Load Superpowers workflow
- `/daily-review` — Import reminders, dashboard, priorities
- Work items: Ask work-tracker agent
- Memory: Ask memory-writer agent

## Code Style
- Python: files under 200 lines, TDD with Superpowers
- TypeScript: strict mode, functional components with hooks

## Architecture
See `docs/ARCHITECTURE.md` for full system details, agents, and skills.

## Tech Stack
- File-native memory (YAML), work tracking (Markdown + YAML frontmatter)
- 9 agents, 25 skills, OutBot (CLI/voice/Telegram) in `brain/`
- Command Centre TUI (Textual) in `brain/command_centre/`
- Hooks: SessionStart, PreToolUse, PostToolUse, Stop
- Zero external dependencies for core system
