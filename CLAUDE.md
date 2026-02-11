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

## Workflow Commands
- Start session: `/using-superpowers`
- Create work item: Ask work-tracker agent
- Update memory: Ask memory-writer agent
- Find information: Check NAVIGATOR.md for grep patterns

## Troy's Preferences
- **ADHD + Dyslexia:** Keep responses short, structured, actionable
- **Australian English** spelling (colour, organise, behaviour)
- **Confirm before executing** changes
- **CLI tools preferred** (gh, git) over MCP where possible
- **YAGNI principle:** Build simplest thing that works
- **Evidence over claims:** Verify before declaring success

## Code Style
- TypeScript strict mode
- Functional components with hooks (React)
- Files under 200 lines where possible
- Test-driven development (TDD) with Superpowers

## Tech Stack (AAGLOBAL)
- File-native memory: YAML-based schemas
- Work tracking: Markdown files with YAML frontmatter
- Agents: work-tracker, memory-writer, navigator-updater
- Hooks: Session start, file change notifications
- Zero external dependencies

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
