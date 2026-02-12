# Memory Navigator
> Grep-optimised index for finding information across domains

## Quick Search Patterns

### Memory System
- Projects: `grep "project_id:" .claude/memory/projects/*.yml`
- Decisions: `grep "decision:" .claude/memory/decisions/*.yml`
- Skills: `grep "skill_name:" .claude/memory/skills/*.yml`
- Patterns: `grep "pattern:" .claude/memory/patterns/*.yml`

### Work Items
- Active PRDs: `grep "status: draft\|in-progress" .claude/work/prd/*.md`
- Open Bugs: `grep "status: open" .claude/work/bugs/*.md`
- Pending Tasks: `grep "status: todo" .claude/work/tasks/*.md`
- All Work Items: `find .claude/work -name "OUT-*.md" -not -path "*/done/*"`
- Completed: `find .claude/work/done -name "OUT-*.md"`

## Domain Map
| Domain | Purpose | Files | Last Updated |
|--------|---------|-------|--------------|
| projects | Active projects & repos | schema.yml, active.yml | 2026-02-11 |
| skills | Learned patterns & techniques | schema.yml, learned.yml | 2026-02-11 |
| patterns | Successful workflows | schema.yml, successful.yml | 2026-02-11 |
| decisions | Architectural choices | schema.yml, architectural.yml | 2026-02-11 |

## Work Items Map
| Type | Folder | Status Options | ID Range |
|------|--------|----------------|----------|
| PRD | .claude/work/prd/ | draft, in-progress, review, done | OUT-001 to OUT-099 |
| Bug | .claude/work/bugs/ | open, investigating, fixing, testing, closed | OUT-101 to OUT-199 |
| Task | .claude/work/tasks/ | todo, doing, done | OUT-201 to OUT-299 |

## Reminders Integration

### Quick Commands
- Import reminders: Ask reminders-importer agent
- Generate dashboard: Ask dashboard-generator agent
- View latest dashboard: `open .claude/dashboards/eisenhower-latest.html`

### Search Patterns
- All reminder tasks: `grep "source: reminder" .claude/work/tasks/*.md`
- Urgent & Important (Q1): `grep "eisenhower_quadrant: q1" .claude/work/tasks/*.md .claude/work/bugs/*.md`
- Important but not urgent (Q2): `grep "eisenhower_quadrant: q2" .claude/work/tasks/*.md .claude/work/bugs/*.md`
- Urgent but not important (Q3): `grep "eisenhower_quadrant: q3" .claude/work/tasks/*.md .claude/work/bugs/*.md`
- Not urgent & not important (Q4): `grep "eisenhower_quadrant: q4" .claude/work/tasks/*.md .claude/work/bugs/*.md`
- Tasks with due dates: `grep -l "due_date: [0-9]" .claude/work/tasks/*.md`
- Overdue tasks: `grep "due_date: 2026-0[12]-" .claude/work/tasks/*.md` (adjust date pattern)
- Import history: `grep -c "Imported from Reminders" .claude/work/tasks/*.md`
- By reminder list: `grep "reminder_list: Shopping" .claude/work/tasks/*.md`

### Configuration
- Import settings: `cat .claude/config/reminders-import.yml`
- Dashboard templates: `ls .claude/templates/`
- Generated dashboards: `ls -lt .claude/dashboards/ | head -10`
- Dashboard archive: `find .claude/dashboards -name "eisenhower-*.html" -mtime +30` (older than 30 days)

## Domain Descriptions
- **projects**: Repository details, tech stacks, deployment configs
- **skills**: Reusable techniques Troy wants to remember
- **patterns**: Workflows that worked well (e.g., TDD, git-flow)
- **decisions**: Important choices made (with rationale)

## Work Item Workflows

### Creating New Work
```bash
# Copy template
cp .claude/work/prd/template.md .claude/work/prd/OUT-042-new-feature.md
# Edit and fill in details
# Commit to git
```

### Completing Work
```bash
# Update status in frontmatter to "done"
# Move to done folder
mv .claude/work/prd/OUT-042-new-feature.md .claude/work/done/prd/
# Commit
```

### Finding Work
```bash
# What's next? (all open work)
grep -l "status: draft\|open\|todo" .claude/work/*/*.md 2>/dev/null | head -5

# High priority items
grep -l "priority: high\|critical" .claude/work/*/*.md 2>/dev/null

# What am I working on?
grep -l "assignee: Troy" .claude/work/*/*.md 2>/dev/null | grep -v done
```
