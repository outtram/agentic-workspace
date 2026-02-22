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
- Import reminders: Ask reminders-importer agent or run `.claude/scripts/import-reminders.py`
- Generate dashboard: Ask dashboard-generator agent or run `.claude/scripts/generate-dashboard.py`
- View latest dashboard: `open .claude/dashboards/eisenhower-latest.html`
- **Mobile dashboard:** https://gist.githack.com/outtram/20f5befb1e2f8cef427b784e6860ddf8/raw/eisenhower-dashboard.html
- Mobile config: `cat .claude/config/mobile-dashboard.yml`

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

## Agents

### Agent Registry
| Agent | File | Purpose | Trigger |
|-------|------|---------|---------|
| reminders-importer | `.claude/agents/reminders-importer.md` | Import macOS Reminders → work items | Daily, manual |
| work-item-enricher | `.claude/agents/work-item-enricher.md` | Enrich bare tasks with real steps + categories | After import, manual |
| overdue-wrangler | `.claude/agents/overdue-wrangler.md` | Review overdue items, propose actions | Daily, manual |
| dashboard-generator | `.claude/agents/dashboard-generator.md` | Generate Eisenhower HTML dashboard | After changes, manual |
| work-tracker | `.claude/agents/work-tracker.md` | CRUD for PRDs/bugs/tasks | On demand |
| memory-writer | `.claude/agents/memory-writer.md` | Update YAML memory domains | On demand |
| navigator-updater | `.claude/agents/navigator-updater.md` | Keep NAVIGATOR.md current | After changes |
| overseer | `.claude/agents/overseer.md` | Orchestrate agents, run pipelines | Session start, daily review |
| meta-agent | `.claude/agents/meta-agent.md` | Detect need for new agents/skills/upgrades | Weekly, manual |

### Agent Search Patterns
- All agents: `ls .claude/agents/*.md`
- Meta-agent review log: `cat .claude/memory/meta-agent-log.yml`
- Agent recommendations: `grep "status:" .claude/memory/meta-agent-log.yml`
- Enriched items: `grep -l "enriched: true" .claude/work/tasks/*.md`
- Wrangler actions: `grep "overdue wrangler" .claude/work/tasks/OUT-*.md .claude/work/done/tasks/OUT-*.md 2>/dev/null`

### Pipelines (run via overseer)
- **Daily review**: reminders-importer → work-item-enricher → overdue-wrangler → dashboard-generator
- **Post-import**: work-item-enricher → dashboard-generator
- **Weekly review**: daily pipeline + meta-agent + navigator-updater + memory-writer

## Documentation
| Document | Path | Purpose |
|---|---|---|
| Architecture | `docs/ARCHITECTURE.md` | Full system architecture with Mermaid diagrams |
| Project Context | `CLAUDE.md` | Root context for Claude Code and Cursor |
| This File | `.claude/memory/NAVIGATOR.md` | Grep-optimised index |
| Root README | `README.md` | Quick start and system overview |
| Laptop Setup | `docs/FRESH-LAPTOP-SETUP.md` | New machine setup guide |
| Reminders Docs | `.claude/reminders/README.md` | Reminders sync system |

### Doc Freshness Check
```bash
# Check architecture doc currency
head -3 docs/ARCHITECTURE.md
# Compare against latest structural changes
ls -lt .claude/agents/*.md brain/*.py docs/*.md | head -10
```

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
