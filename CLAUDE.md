# CLAUDE.md

## Project: AAGLOBAL
> Troy Outtram's agentic development environment

## Memory System
This project uses a **file-native memory system** based on research by Damon McMillan (2026).

**Quick Navigation:**
- Memory Navigator: `.claude/memory/NAVIGATOR.md`
- Active Projects: `.claude/memory/projects/active.yml`
- Open Work Items: `.claude/work/` (prd/bugs/tasks)
- Learned Skills: `.claude/memory/skills/learned.yml`

**Grep Patterns:**
```bash
# Find active projects
grep "status: active" .claude/memory/projects/*.yml

# Find open work items
grep -l "status: draft\|open\|todo" .claude/work/*/*.md 2>/dev/null

# Find high priority work
grep -l "priority: high\|critical" .claude/work/*/*.md 2>/dev/null

# Find architectural decisions
grep "decision:" .claude/memory/decisions/*.yml
```

## Repository Strategy
- **Source Control:** GitHub (github.com/Outtram)
- **Work Tracking:** File-based (.claude/work/ - PRDs, bugs, tasks)
- **Branching:** main (prod), dev (staging), feature/OUT-XX-description
- **Commits:** Prefix with work item ID: `OUT-XX: description`

## Shared Memory (OutBot + Claude Code)
When Troy says "remember X" or "don't forget X", write to the **shared** memory files so OutBot can see it too:
```bash
python3 .claude/scripts/shared_memory.py write "content here" user_pref|personality|fact
python3 .claude/scripts/shared_memory.py forget "search term"
python3 .claude/scripts/shared_memory.py search "query"
```
This writes to `.claude/memory/USER.md` (preferences) or `.claude/memory/LEARNED.md` (facts) — the same files OutBot reads via its personality loader. Use this **in addition to** auto-memory for cross-system visibility.

## Workflow Commands
- Start session: `/using-superpowers`
- Create work item: Ask work-tracker agent
- Update memory: Ask memory-writer agent
- **Remember something:** `python3 .claude/scripts/shared_memory.py write "content" category`
- Find information: Check NAVIGATOR.md for grep patterns
- **Daily review:** `/daily-review` or say "do my daily review"
- **Import reminders:** Say "import my reminders" or "sync reminders"
- **View priorities:** Say "show me my Q1 tasks" or "what should I work on?"

## Troy's Preferences
- **ADHD + Dyslexia:** Keep responses short, structured, actionable
- **Australian English** spelling (colour, organise, behaviour)
- **Confirm before executing** changes
- **CLI tools preferred** (gh, git) over MCP where possible
- **YAGNI principle:** Build simplest thing that works
- **Evidence over claims:** Verify before declaring success

## Command Centre Help Sources (MANDATORY)
When modifying ANY Command Centre file (`brain/command_centre/`), you MUST update ALL of these before committing:
1. **`HELP.md`** — the master help file
2. **`brain/command_centre/app.py`** — the `_HELP_TEXT` string (? overlay)
3. **`brain/command_centre/router.py`** — the `/help` command output
4. **`docs/ARCHITECTURE.md`** — if adding new features

A pre-commit hook will block commits that change CC files without updating help. A Claude Code hook will remind you on every edit. No exceptions.

## Daily Routine Automation
When Troy says any of these phrases, automatically run the daily review workflow:
- "do my daily review"
- "import my reminders" / "sync reminders"
- "what should I work on?" / "show me my Q1"
- "start my day" / "daily priorities"

**Workflow:**
1. Import reminders from macOS Reminders
2. Generate Eisenhower Matrix dashboard
3. Update mobile gist (https://gist.githack.com/outtram/20f5befb1e2f8cef427b784e6860ddf8/raw/eisenhower-dashboard.html)
4. Show Q1 priorities (urgent & important)
5. Offer to start a task or update status

## Code Style
- TypeScript strict mode
- Functional components with hooks (React)
- Files under 200 lines where possible
- Test-driven development (TDD) with Superpowers

## System Architecture
For the full system architecture including diagrams, component details, and how Claude Code agents relate to OutBot, see **`docs/ARCHITECTURE.md`**.

## Tech Stack (AAGLOBAL)
- File-native memory: YAML-based schemas
- Work tracking: Markdown files with YAML frontmatter
- Agents: 9 agents (overseer, enricher, wrangler, tracker, importer, dashboard, memory-writer, navigator-updater, meta-agent)
- Skills: 18 skills (pptx, daily-review, TDD, design, etc.)
- OutBot: Conversational AI (CLI, voice, WhatsApp) in `brain/`
- Hooks: Session start, file change notifications
- Zero external dependencies for core system

## Research Foundation
Based on "Structured Context Engineering for File-Native Agentic Systems" (Damon McMillan, 2026):
- YAML: 28-60% more token-efficient than JSON/Markdown
- File-native retrieval: +2.7% accuracy for Claude
- Domain partitioning: scales to 10,000 tables
- Grep-friendly patterns: sub-second discovery

## Next Steps
When starting a session:
1. Run `/using-superpowers` to load Superpowers workflow
2. Check `.claude/memory/NAVIGATOR.md` for grep patterns
3. Review open work items: `grep -l "status: draft\|open\|todo" .claude/work/*/*.md 2>/dev/null`
4. Ask work-tracker agent to create/update work items as needed
5. Use memory-writer agent to document new learnings
