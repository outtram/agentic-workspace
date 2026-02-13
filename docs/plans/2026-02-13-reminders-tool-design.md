# Reminders Management Tool - Design Document

**Date:** 2026-02-13
**Author:** Claude Sonnet 4.5
**Status:** Approved
**Version:** 1.0

## Executive Summary

This document specifies the design for a bi-directional sync system between macOS Reminders.app and the file-native task management system in AAGLOBAL. The system provides CLI, Python API, and Claude Code integration for managing reminders with AI-powered enrichment.

**Key Features:**
- Bi-directional sync between Reminders.app and work item files
- Multi-dimensional tagging (projects, contexts, priorities)
- Intelligent conflict resolution with manual review
- AI enrichment with proactive suggestions and guardrails
- Event-driven architecture supporting future TUI/web interfaces
- Hook integration with Claude Code for immediate push on local changes

## 1. Architecture & Core Components

### 1.1 Module Structure

```
.claude/reminders/
├── core/
│   ├── __init__.py
│   ├── manager.py          # RemindersManager (main API)
│   ├── events.py           # Event bus & event types
│   └── models.py           # WorkItem, Reminder data models
├── adapters/
│   ├── applescript.py      # Reminders.app interface
│   └── workitems.py        # Work item file I/O
├── sync/
│   ├── engine.py           # Sync orchestration
│   ├── conflicts.py        # Conflict detection & resolution
│   └── state.py            # Sync state tracking
├── enrichment/
│   ├── agent.py            # AI enrichment suggestions
│   ├── guardrails.py       # Safety rules
│   └── learning.py         # Learn from user choices
├── plugins/
│   ├── base.py             # Plugin interface
│   └── cli.py              # CLI plugin
└── hooks/
    └── claude_code.py      # Claude Code hook integration
```

### 1.2 Key Principles

- **RemindersManager** is the public API - everything goes through it
- **Event bus** decouples components (sync doesn't know about AI enrichment)
- **Adapters** abstract Reminders.app and work item files (swappable for testing)
- **Plugins** register themselves, no hardcoded UI dependencies in core

### 1.3 Event-Driven Architecture

```
┌─────────────────────────────────────┐
│  Interfaces (Plugins)               │
│  - CLI wrapper                      │
│  - Python API                       │
│  - Future: TUI, Web                 │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Core: RemindersManager             │
│  - Event bus (pub/sub)              │
│  - Sync engine                      │
│  - Conflict detector                │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Event Subscribers                  │
│  - Hook integration (PostToolUse)   │
│  - AI enrichment agent              │
│  - Conflict resolver UI             │
└─────────────────────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Data Layer                         │
│  - AppleScript adapter              │
│  - Work item file manager           │
│  - Sync state tracker               │
└─────────────────────────────────────┘
```

**Why Event-Driven:**
- AI enrichment fits naturally as event subscriber
- Hook integration is cleanest (hooks publish events)
- Future TUI/web just subscribe to events
- Clean testing (mock event bus)
- Scales to more complex workflows

## 2. Data Layer & Multi-Dimensional Tags

### 2.1 Data Models

**WorkItem (file representation):**
```python
{
    "id": "OUT-241",
    "title": "equity partner nomination form is due 20th feb",
    "tags": ["equity-partner", "admin", "deloitte", "urgent"],
    "tag_categories": {
        "project": ["equity-partner"],
        "context": ["admin"],
        "client": ["deloitte"],
        "priority": ["urgent"]
    },
    "status": "todo",
    "priority": "high",
    "due_date": "2026-02-20",
    "eisenhower_quadrant": "q1",
    "eisenhower_urgent": true,
    "eisenhower_important": true,
    "source": "reminder",
    "reminder_id": "x-apple-reminder://ABC123",
    "reminder_list": "Reminders",
    "branch": "task/OUT-241-equity-partner-form",
    "description": "Fill out form...",
    "steps": [...],
    "updated": "2026-02-13T14:50:00"
}
```

**Reminder (Reminders.app via AppleScript):**
```python
{
    "id": "x-apple-reminder://ABC123",
    "name": "equity partner nomination form is due 20th feb",
    "body": "---\nOUT-241\neisenhower_quadrant: q1\n...\n---\nFill out form...",
    "tags": ["equity-partner", "admin", "deloitte", "urgent"],
    "due_date": "2026-02-20T00:00:00",
    "priority": 1,  # 0=none, 1=high, 5=medium, 9=low
    "list": "Reminders",
    "completed": false,
    "modified": "2026-02-13T14:50:00"
}
```

### 2.2 Tag Categories

Multi-dimensional tagging for maximum flexibility:

```yaml
# .claude/reminders/config/tag-schema.yml
categories:
  project:
    description: "Major initiatives and work streams"
    examples: [aussuper, equity-partner, continuous-delivery, labs]

  context:
    description: "GTD contexts - where/when/how"
    examples: [phone, computer, meeting, waiting, someday, online]

  client:
    description: "Client/company associations"
    examples: [deloitte, aussuper-client, internal]

  priority:
    description: "Priority signals (supplements eisenhower)"
    examples: [urgent, important, quick-win, delegate]

  area:
    description: "Life areas"
    examples: [work, personal, health, home, learning]

  status:
    description: "Workflow states"
    examples: [blocked, in-progress, review-needed, waiting-approval]
```

### 2.3 Metadata Embedding

Work item metadata stored in Reminders body field as YAML frontmatter:

```
---
OUT-241
eisenhower_quadrant: q1
eisenhower_urgent: true
eisenhower_important: true
branch: task/OUT-241-equity-partner-form
assignee: Troy
---
Fill out equity partner nomination form.

Steps:
- [ ] Download form
- [ ] Complete sections 1-5
- [ ] Submit by Feb 20
```

**Benefits:**
- Human-readable on phone/desktop
- Machine-parseable for round-trip
- Graceful degradation if metadata corrupted

### 2.4 Sync State Tracking

```
.claude/reminders/.sync-state/
├── last-sync.json          # Timestamp of last successful sync
├── conflicts.json          # Active conflicts awaiting resolution
├── mappings.json           # OUT-ID ↔ reminder-id mappings
└── failed-operations.json  # Pending retries
```

### 2.5 Bi-Directional Sync Flow

**Push (immediate on local change):**
```
Work item edited
→ Event: WorkItemUpdated(OUT-241)
→ Sync engine: Load reminder_id from work item
→ AppleScript: Update reminder in Reminders.app
→ Update mappings.json
```

**Pull (on daily review):**
```
Daily review triggered
→ AppleScript: Fetch all active reminders
→ For each reminder:
    - Check if reminder_id exists in mappings.json
    - YES: Compare timestamps, detect conflicts
    - NO: Create new work item (import)
→ Resolve conflicts interactively
→ Update last-sync.json
```

**Conflict Detection:**
```
Reminder modified: 2026-02-13 10:00 AM
Work item modified: 2026-02-13 11:30 AM
Last sync: 2026-02-12 09:00 AM

→ Both changed since last sync = CONFLICT
→ Add to conflicts.json
→ Show during daily review
```

## 3. Event System

### 3.1 Event Types

```python
# Work Item Events
WorkItemCreated(work_item_id, reminder_id)
WorkItemUpdated(work_item_id, changes)
WorkItemCompleted(work_item_id)
WorkItemDeleted(work_item_id)

# Reminder Events
ReminderPushed(work_item_id, reminder_id, success)
ReminderPulled(reminder_id, work_item_id)

# Sync Events
SyncStarted(sync_type)
SyncCompleted(pushed, pulled, conflicts)
ConflictDetected(work_item_id, reminder_id, ...)
ConflictResolved(work_item_id, resolution)

# Enrichment Events
EnrichmentSuggested(work_item_id, suggestions)
EnrichmentApplied(work_item_id, applied)
```

### 3.2 Event Flow Examples

**Creating a Reminder:**
```python
# 1. CLI calls RemindersManager
rm.create_reminder("Call Leon", due_date="2026-02-14", tags=["phone"])

# 2. Manager creates work item file
work_item = create_work_item_file(...)
bus.publish(WorkItemCreated(work_item_id="OUT-264"))

# 3. Subscribers react:
#    - SyncEngine: Push to Reminders.app
#    - HookIntegration: Notify Claude Code
#    - EnrichmentAgent: Suggest tags ["waiting", "urgent"]?

# 4. SyncEngine pushes
success = applescript_adapter.create_reminder(...)
bus.publish(ReminderPushed(work_item_id="OUT-264", success=True))
```

**Daily Review (Pull):**
```python
# 1. Trigger sync
bus.publish(SyncStarted(sync_type="pull"))

# 2. Fetch all reminders
reminders = applescript_adapter.fetch_all_reminders()

# 3. Detect conflicts
for reminder in reminders:
    if both_modified_since_last_sync(work_item, reminder):
        bus.publish(ConflictDetected(...))

# 4. Show resolution UI for conflicts

# 5. Complete sync
bus.publish(SyncCompleted(pushed=0, pulled=15, conflicts=2))

# 6. AI enrichment suggests improvements
for work_item in newly_imported:
    bus.publish(EnrichmentSuggested(...))
```

## 4. Conflict Resolution

### 4.1 Detection Logic

```python
def detect_conflict(work_item, reminder, last_sync_time):
    """Conflict occurs when BOTH changed since last sync"""
    work_item_changed = work_item.updated > last_sync_time
    reminder_changed = reminder.modified > last_sync_time

    return work_item_changed and reminder_changed
```

### 4.2 Conflict Data Structure

```json
{
  "OUT-241": {
    "detected_at": "2026-02-13T14:50:00",
    "work_item_snapshot": {...},
    "reminder_snapshot": {...},
    "diff": {
      "title": "CHANGED_BOTH",
      "due_date": "CHANGED_BOTH",
      "tags": "CHANGED_WORK_ITEM_ONLY"
    }
  }
}
```

### 4.3 Resolution Options

**CLI Interactive Resolution:**
```bash
⚠️  SYNC CONFLICTS DETECTED (2 conflicts)

Conflict #1: OUT-241 (equity partner nomination form)

Field: due_date
  📱 Reminders:  2026-02-19
  💻 Work item:  2026-02-20

Choose resolution:
  [R] Use Reminders version (phone wins)
  [W] Use Work item version (local wins)
  [M] Merge manually (pick field by field)
  [S] Skip for now

Your choice:
```

**Claude Code Integration:**
During `/daily-review`, conflicts presented conversationally:
```
🔍 Found 2 conflicts during sync:

1. OUT-241 (equity partner form)
   - You changed the due date to Feb 20 locally
   - On your phone, you changed it to Feb 19

   Which version should I keep?
```

### 4.4 Auto-Resolution Rules (Future)

```yaml
# .claude/reminders/config/resolution-rules.yml
rules:
  - condition: "reminder.completed == true"
    action: "reminder_wins"
    reason: "Phone completion always wins"

  - condition: "work_item.tags changed AND reminder.tags unchanged"
    action: "work_item_wins"
    reason: "Local tag enrichment should be preserved"
```

## 5. Error Handling & Resilience

### 5.1 Error Categories

- **AppleScript Errors**: Reminders.app unavailable, timeout, permissions
- **Sync Errors**: Conflicts, corrupted state
- **Work Item Errors**: File not found, malformed frontmatter
- **Reminder Errors**: Reminder not found, invalid data

### 5.2 Retry Strategy

```python
@retry(max_attempts=3, backoff=2.0, exceptions=[AppleScriptTimeoutError])
def fetch_all_reminders():
    """Fetch reminders with automatic retry"""
    return applescript.execute(FETCH_REMINDERS_SCRIPT)
```

### 5.3 Graceful Degradation

```python
def create_reminder(title, **kwargs):
    try:
        # Create work item + push to Reminders
        work_item = create_work_item_file(title, **kwargs)
        push_to_reminders_app(work_item)
    except RemindersAppError:
        # Fall back: create work item only, queue for later sync
        work_item = create_work_item_file(title, **kwargs)
        queue_for_sync(work_item.id)
    return work_item
```

### 5.4 Sync Recovery

```json
// .claude/reminders/.sync-state/failed-operations.json
{
  "pending_pushes": [
    {
      "work_item_id": "OUT-264",
      "operation": "create",
      "attempts": 2,
      "last_error": "AppleScriptTimeoutError"
    }
  ]
}
```

On next sync, retry failed operations. After 5 attempts, move to dead letter queue.

### 5.5 Data Integrity

- Validate before writing
- Backup before applying changes
- Rollback on failure
- Rebuild sync state from sources if corrupted

### 5.6 Diagnostic Tool

```bash
$ reminder-diagnose

🔍 Reminders System Diagnostics

✅ Reminders.app is running
✅ Permissions granted
⚠️  Sync state has 2 pending operations
❌ Conflicts.json is corrupted

Issues found:
1. Run 'reminder-sync --repair' to fix corrupted state
2. Run 'reminder-sync --retry' for 2 pending pushes

Overall health: DEGRADED
```

## 6. CLI Interface

### 6.1 Command Structure

```bash
reminder <command> [arguments] [options]

Commands:
  add         Create a new reminder
  complete    Mark reminder as done
  edit        Update reminder fields
  delete      Delete a reminder
  list        List reminders with filters
  sync        Sync with Reminders.app
  show        Show detailed reminder info
  tags        Manage tags
  enrich      AI enrichment operations
  diagnose    Run system diagnostics
  config      View/edit configuration
```

### 6.2 Core Command Examples

**Add:**
```bash
reminder add "Call Leon Doyle" \
  --due tomorrow \
  --priority high \
  --tag phone --tag urgent \
  --notes "Discuss equity partner timeline"
```

**List with Filters:**
```bash
reminder list --tag aussuper
reminder list --q1  # Urgent & important
reminder list --overdue
reminder list --format json
```

**Sync:**
```bash
reminder sync              # Full bi-directional
reminder sync --push       # Push only
reminder sync --pull       # Pull only
reminder sync --dry-run    # Show what would change
```

**Enrichment:**
```bash
reminder enrich OUT-241                    # Enrich specific item
reminder enrich --q1                       # Enrich all Q1 items
reminder enrich OUT-241 --auto-apply       # Auto-apply suggestions
```

### 6.3 Output Formatting

```bash
# Table format (default)
┌─────────┬────────────────────────┬──────────┬──────────┐
│ ID      │ Title                  │ Due      │ Tags     │
├─────────┼────────────────────────┼──────────┼──────────┤
│ OUT-247 │ Aus super store front  │ Jan 30   │ aussuper │
└─────────┴────────────────────────┴──────────┴──────────┘

# Compact format
OUT-247  Aus super store front

# JSON format (for scripting)
[{"id": "OUT-247", "title": "Aus super store front", ...}]
```

### 6.4 Shell Completion

```bash
reminder completion install

# Then tab completion works
$ reminder list --tag <TAB>
aussuper  equity-partner  phone  urgent
```

## 7. AI Enrichment System

### 7.1 Architecture

```python
class EnrichmentAgent:
    """Proactive AI assistant for enriching reminders"""

    def analyze_work_item(self, work_item_id):
        # Gather context from multiple sources
        context = {
            "related_items": find_related_work_items(),
            "recent_commits": scan_recent_commits(),
            "related_files": search_workspace(),
            "similar_completed": find_similar_tasks(),
            "tag_patterns": analyze_tag_patterns()
        }

        # Generate suggestions
        suggestions = generate(work_item, context)
        return suggestions
```

### 7.2 Suggestion Types

**1. Tag Suggestions:**
```python
{
    "tags": {
        "add": ["equity-partner", "deloitte", "admin"],
        "reasoning": "Found 'equity partner' in title, 'deloitte' in files"
    }
}
```

**2. Step Breakdown:**
```python
{
    "steps": {
        "suggested_steps": [
            "Download nomination form",
            "Complete sections 1-5",
            "Submit by Feb 20"
        ]
    }
}
```

**3. Related Items:**
```python
{
    "links": {
        "related_items": [
            {"id": "OUT-142", "reason": "Same project, has contact info"}
        ]
    }
}
```

**4. Priority/Quadrant Adjustments:**
```python
{
    "classification": {
        "suggested_priority": "high",
        "reasoning": "Due in 7 days, career-critical"
    }
}
```

### 7.3 Presentation (Daily Review)

```bash
💡 AI Enrichment Suggestions (5 items)

1. OUT-241 (equity partner nomination form)

   🏷️  Suggested tags: #equity-partner #deloitte #admin
   ⚠️  Priority adjustment: low → high
   📋 Suggested steps: [Download form, Complete, Submit]
   🔗 Related: OUT-142 (has contact info)

   Apply suggestions? [all/tags/priority/steps/links/skip]:
```

### 7.4 Guardrails

```python
RULES = {
    # Never auto-apply
    "forbidden_auto_apply": [
        "delete_work_item",
        "change_due_date_backward",
        "mark_completed"
    ],

    # Always ask before applying
    "require_confirmation": [
        "change_priority",
        "add_due_date",
        "change_eisenhower_quadrant"
    ],

    # Can auto-apply if confidence > 0.8
    "auto_apply_high_confidence": [
        "add_tags",
        "suggest_steps",
        "link_related_items"
    ],

    # Limits
    "max_tags_per_suggestion": 5,
    "max_steps_per_suggestion": 8
}
```

### 7.5 Learning from User Choices

```json
// .claude/reminders/.learning/suggestion-history.json
{
  "2026-02-13T15:00:00": {
    "work_item_id": "OUT-241",
    "suggestion_type": "tags",
    "suggested": ["equity-partner", "admin", "urgent"],
    "user_accepted": ["equity-partner", "admin"],
    "user_rejected": ["urgent"],
    "confidence_was": 0.85
  }
}
```

System adjusts future confidence based on acceptance/rejection patterns.

### 7.6 Enrichment Triggers

- **Daily review** - Analyze all Q1, new imports, overdue items
- **On create** - Suggest tags immediately
- **On update** - Reanalyze if title changed
- **Manual** - `reminder enrich OUT-241`

## 8. Testing Strategy

### 8.1 Test Structure

```
tests/
├── unit/              # Fast, isolated tests
├── integration/       # Test with real components
├── e2e/              # End-to-end scenarios
├── fixtures/          # Mock data
└── conftest.py       # Pytest configuration
```

### 8.2 Mock AppleScript Layer

```python
class MockAppleScriptAdapter:
    """Mock Reminders.app for testing without real app"""

    def __init__(self):
        self.reminders = {}  # In-memory store
        self.call_log = []   # Track calls
```

### 8.3 Coverage Targets

- `core/`: 90% (critical business logic)
- `sync/`: 85% (sync engine)
- `adapters/`: 70% (external integrations)
- `enrichment/`: 75% (AI features)
- `plugins/cli.py`: 80% (user-facing)

### 8.4 Continuous Testing

```yaml
# GitHub Actions workflow
- Run unit tests
- Run integration tests
- Run E2E tests (mock only)
- Generate coverage report
- Fail if coverage < 80%
```

## 9. Claude Code Integration

### 9.1 Hook Integration

**PostToolUse Hook:**
```python
# .claude/hooks/post-tool-use.py

def on_post_tool_use(tool_name, args, result):
    """Trigger push when work item edited"""
    if tool_name == "Edit" and is_work_item_file(args.file_path):
        # Extract work item ID
        work_item_id = extract_id_from_path(args.file_path)

        # Push to Reminders.app
        subprocess.run(["reminder", "sync", "--push", work_item_id])
```

**Daily Review Integration:**
```bash
# /daily-review skill calls:
1. reminder sync --pull    # Pull from Reminders.app
2. [resolve conflicts]
3. reminder enrich --q1     # Suggest enrichments
4. [generate dashboard]
```

### 9.2 Claude Natural Language Interface

```python
# When user says: "Add reminder to call Leon tomorrow"
rm = RemindersManager()
rm.create_reminder(
    "Call Leon",
    due_date=parse_natural_date("tomorrow"),
    tags=["phone"]
)

# When user says: "Mark OUT-251 as done"
rm.complete_reminder("OUT-251")

# When user says: "Show me all AusSuper tasks"
tasks = rm.list_reminders(tags=["aussuper"])
```

## 10. Future Enhancements

### 10.1 TUI Interface (Terminal UI)

```python
# .claude/reminders/plugins/tui.py

class TUIPlugin(Plugin):
    """Terminal UI using Rich/Textual"""

    def render_dashboard(self):
        # Real-time dashboard
        # Subscribe to events for live updates
        pass
```

### 10.2 Web Interface

```python
# .claude/reminders/plugins/web.py

class WebPlugin(Plugin):
    """Web UI using FastAPI + HTMX"""

    def start_server(self):
        # Web dashboard
        # WebSocket for real-time sync events
        pass
```

### 10.3 Advanced Enrichment

- Context from calendar events
- Email integration for task extraction
- Slack/Teams message parsing
- Voice input for task creation
- Smart scheduling (optimal time suggestions)

### 10.4 Collaboration Features

- Shared reminders (family/team)
- Delegation tracking
- Progress sharing
- Comment threads on tasks

## 11. Implementation Phases

### Phase 1: Core Foundation (v0.1)
- [ ] Basic Python API (RemindersManager)
- [ ] AppleScript adapter (read/write reminders)
- [ ] Work item file I/O
- [ ] Simple CLI (add, list, complete)
- [ ] Unit tests

### Phase 2: Sync Engine (v0.2)
- [ ] Event bus implementation
- [ ] Bi-directional sync (push/pull)
- [ ] Conflict detection
- [ ] Manual conflict resolution
- [ ] Sync state tracking

### Phase 3: Tags & Enrichment (v0.3)
- [ ] Multi-dimensional tags
- [ ] Tag categorization
- [ ] Basic AI enrichment (tag suggestions)
- [ ] Guardrails system
- [ ] Learning from user choices

### Phase 4: Integration (v0.4)
- [ ] Claude Code hooks
- [ ] Daily review integration
- [ ] Advanced enrichment (steps, links)
- [ ] Shell completion
- [ ] Comprehensive CLI

### Phase 5: Polish (v1.0)
- [ ] Error handling & resilience
- [ ] Diagnostic tools
- [ ] Documentation
- [ ] E2E tests
- [ ] Performance optimization

## 12. Success Criteria

**Technical:**
- ✅ Bi-directional sync with < 1 second latency
- ✅ Zero data loss (all operations recoverable)
- ✅ 80%+ test coverage
- ✅ Handles 100+ reminders without performance degradation

**User Experience:**
- ✅ ADHD-friendly (clear, visual, minimal friction)
- ✅ Conflicts resolvable in < 30 seconds
- ✅ AI suggestions useful (>70% acceptance rate)
- ✅ Natural integration with existing workflow

**Reliability:**
- ✅ Graceful degradation when Reminders.app unavailable
- ✅ Automatic recovery from transient failures
- ✅ Clear error messages with actionable fixes

## 13. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| AppleScript API changes | High | Abstract via adapter layer, version detection |
| Sync conflicts overwhelming | Medium | Smart auto-resolution rules, batch operations |
| Performance with many reminders | Low | Pagination, incremental sync, indexing |
| AI suggestions annoying | Medium | Guardrails, learning system, opt-out |
| Data corruption | High | Backups, validation, sync state repair |

## 14. Dependencies

**Python Libraries:**
- `click` - CLI framework
- `pyyaml` - Config & frontmatter parsing
- `python-dateutil` - Natural date parsing
- `rich` - Terminal formatting (future TUI)
- `pytest` - Testing framework

**System Requirements:**
- macOS 12+ (for AppleScript API)
- Python 3.11+
- Terminal with Reminders.app permissions

**Integration:**
- Claude Code (hooks, /daily-review skill)
- Git (for work item version control)
- GitHub Gist (for mobile dashboard)

## 15. Configuration

```yaml
# .claude/reminders/config/settings.yml

sync:
  auto_push: true                    # Push on local changes
  auto_pull_on_daily_review: true    # Pull during /daily-review
  conflict_resolution: "manual"      # manual | auto | rules

enrichment:
  enabled: true
  auto_apply_threshold: 0.8          # Confidence threshold
  max_suggestions_per_review: 10
  learn_from_choices: true

tags:
  schema_file: "tag-schema.yml"
  auto_categorize: true
  suggest_on_create: true

cli:
  default_format: "table"            # table | json | compact
  color_output: true
  confirm_destructive: true

logging:
  level: "INFO"                      # DEBUG | INFO | WARNING | ERROR
  file: ".claude/reminders/logs/reminders.log"
  max_size_mb: 10
```

## Conclusion

This design provides a robust, extensible foundation for bi-directional reminder management with AI enrichment. The event-driven architecture supports future enhancements (TUI, web interface) while maintaining simplicity for v1. The multi-dimensional tagging system and proactive AI enrichment align with Troy's vision of an intelligent task management system that grows more helpful over time.

**Next Steps:**
1. Review and approve design
2. Create implementation plan with detailed tasks
3. Begin Phase 1: Core Foundation
