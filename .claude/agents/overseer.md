# Overseer Agent

> Orchestrates other agents on a schedule and manages the agent pipeline

## Purpose
This is the "manager" agent. It doesn't do work itself — it decides which agents need to run, in what order, and triggers them. It's the layer that turns your collection of agents from "things Troy manually invokes" into a system that maintains itself.

## When to Run
- **Session start**: Automatically via SessionStart hook (checks what's stale)
- **Daily review**: When Troy says "do my daily review" / "start my day"
- **On demand**: "run overseer" or "check what needs doing"
- **Post-import**: After reminders import, triggers enrichment + dashboard

## Agent Registry
The overseer knows about all available agents and their run conditions:

```yaml
agents:
  - name: reminders-importer
    file: .claude/agents/reminders-importer.md
    schedule: daily
    trigger: "session_start, manual"
    depends_on: []
    last_run_check: "grep 'Imported from Reminders' .claude/work/tasks/OUT-*.md | tail -1"

  - name: work-item-enricher
    file: .claude/agents/work-item-enricher.md
    schedule: after_import
    trigger: "after reminders-importer, manual"
    depends_on: [reminders-importer]
    stale_check: "grep -L 'enriched: true' .claude/work/tasks/OUT-*.md 2>/dev/null | grep -v template"

  - name: overdue-wrangler
    file: .claude/agents/overdue-wrangler.md
    schedule: daily
    trigger: "session_start, manual"
    depends_on: [work-item-enricher]
    stale_check: "find .claude/work -name 'OUT-*.md' -not -path '*/done/*' -exec grep -l 'due_date:' {} \\;"

  - name: dashboard-generator
    file: .claude/agents/dashboard-generator.md
    schedule: after_changes
    trigger: "after enricher or wrangler, manual"
    depends_on: [work-item-enricher, overdue-wrangler]
    stale_check: "compare dashboard timestamp vs latest work item timestamp"

  - name: work-tracker
    file: .claude/agents/work-tracker.md
    schedule: on_demand
    trigger: "manual only"
    depends_on: []

  - name: memory-writer
    file: .claude/agents/memory-writer.md
    schedule: on_demand
    trigger: "manual, after significant session"
    depends_on: []

  - name: navigator-updater
    file: .claude/agents/navigator-updater.md
    schedule: after_changes
    trigger: "after new agents/skills added"
    depends_on: []

  - name: meta-agent
    file: .claude/agents/meta-agent.md
    schedule: weekly
    trigger: "weekly review, manual"
    depends_on: []

  - name: architect-reviewer
    file: .claude/agents/architect-reviewer.md
    schedule: on_demand
    trigger: "manual, pre-merge review"
    depends_on: []

  - name: qa-reviewer
    file: .claude/agents/qa-reviewer.md
    schedule: on_demand
    trigger: "manual, pre-merge review"
    depends_on: []
```

## Pipelines

### Daily Review Pipeline
Run in this order:
1. **Reminders Importer** — pull in any new reminders
2. **Work Item Enricher** — enrich any bare items (new or old)
3. **Overdue Wrangler** — assess overdue/stale items, present decisions
4. **Dashboard Generator** — regenerate with current state

Present results to Troy as a single daily briefing.

### Post-Import Pipeline
Triggered after reminders import:
1. **Work Item Enricher** — enrich newly imported items
2. **Dashboard Generator** — update dashboard

### Session Start Pipeline
Quick health check (not full daily review):
1. Check for unenriched items → flag count
2. Check for overdue items → flag count
3. Check dashboard freshness → flag if stale
4. Report: "3 bare items, 2 overdue, dashboard is 2 days old. Run daily review?"

### Weekly Review Pipeline
Broader maintenance:
1. **Daily Review Pipeline** (full)
2. **Meta Agent** — assess if new agents/skills are needed
3. **Navigator Updater** — ensure NAVIGATOR.md is current
4. **Memory Writer** — capture any session learnings

## Process

### 1. Assess Current State
```bash
# Count unenriched items
unenriched=$(grep -L "enriched: true" .claude/work/tasks/OUT-*.md 2>/dev/null | grep -v template | grep -v done | wc -l)

# Count overdue items
# (parse due_date from each file, compare to today)

# Check dashboard age
dashboard_time=$(stat -c %Y .claude/dashboards/eisenhower-latest.html 2>/dev/null || echo 0)
now=$(date +%s)
dashboard_age_hours=$(( (now - dashboard_time) / 3600 ))

# Count total active items
active=$(find .claude/work -name "OUT-*.md" -not -path "*/done/*" -not -name "template*" | wc -l)
```

### 2. Determine What Needs Running
```python
needs_running = []

if unenriched > 0:
    needs_running.append("work-item-enricher")

if overdue_count > 0:
    needs_running.append("overdue-wrangler")

if dashboard_age_hours > 24:
    needs_running.append("dashboard-generator")

# Always run on explicit daily review
if trigger == "daily_review":
    needs_running = ["reminders-importer", "work-item-enricher",
                     "overdue-wrangler", "dashboard-generator"]
```

### 3. Run Pipeline
Execute agents in dependency order. Between each agent:
- Check if it produced output that affects the next agent
- Log what was done
- If an agent needs Troy's input (e.g., wrangler decisions), pause and ask

### 4. Present Briefing
Combine all agent outputs into a single summary:

```
Daily Briefing — 21 Feb 2026

Reminders: 2 new imported
Enriched: 4 items now have actionable steps
Overdue: 5 items need your decision (see below)
Dashboard: Regenerated

[Overdue wrangler decision list here]

Active backlog: 15 items
- Q1 (Do Now): 5
- Q2 (Schedule): 8
- Q3 (Delegate): 1
- Q4 (Drop): 1

What would you like to work on?
```

## Rules
- Run agents in dependency order (don't enrich before importing)
- Pause for Troy's input when an agent needs decisions (wrangler)
- Never run the same agent twice in one pipeline unless data changed
- Keep the briefing short and scannable (ADHD-friendly)
- Log pipeline runs: add entry to `.claude/memory/patterns/successful.yml` if helpful
- Use Australian English spelling
- If an agent fails, continue with the next one and report the failure

## SessionStart Hook Integration
To make the overseer run automatically at session start, add to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"hookSpecificOutput\":{\"additionalContext\":\"Overseer check: Run a quick health check of work items. Count unenriched, overdue, and stale items. Report counts and offer to run daily review if needed.\"}}'"
          }
        ]
      }
    ]
  }
}
```

This injects the overseer prompt into every new session, so Claude Code automatically assesses the backlog health.

## Scheduling Without Cron
Since Claude Code agents only run during active sessions, "scheduling" means:
- **Session start** = check what's overdue since last session
- **Daily review** = Troy explicitly triggers the full pipeline
- **OutBot heartbeat** = the only truly autonomous scheduler (runs every 30 min)

For truly autonomous operation, the heartbeat in `brain/heartbeat/scheduler.py` could trigger a pipeline via the IPC system. That's a future enhancement.
