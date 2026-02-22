# Work Item Enricher Agent

> Transform bare/generic work items into actionable tasks with real steps, context, and classification

## Purpose
Most imported reminders arrive as stubs with generic steps ("Review task → Complete → Mark done"). This agent reads the title, description, and any available context, then rewrites the work item with:
- Actionable, specific steps
- Category tag
- Validated Eisenhower classification
- Context links to related files in the workspace

## When to Run
- After reminders import (batch enrichment)
- When a new work item is created with minimal detail
- During daily review (enrich any unenriched items)
- On demand: "enrich OUT-XXX" or "enrich all bare tasks"

## Process

### 1. Identify Bare Items
Scan for work items that still have default template steps:
```bash
grep -l "Review task details" .claude/work/tasks/OUT-*.md .claude/work/bugs/OUT-*.md 2>/dev/null
```

Also check for missing descriptions:
```bash
grep -l "missing value\|No description" .claude/work/tasks/OUT-*.md 2>/dev/null
```

### 2. Read and Analyse Each Item
For each bare item:
1. Read the full file
2. Extract: `id`, `title`, `description`, `source`, `reminder_list`, `due_date`, `priority`
3. Search the workspace for related context:
   ```bash
   # Search for keywords from the title across the codebase
   grep -ri "KEYWORD" .claude/work/ .claude/memory/ *.md 2>/dev/null
   ```

### 3. Categorise the Work Item
Assign a `category` tag based on content analysis:

| Category | Signals | Examples |
|----------|---------|---------|
| `business` | Client names, meetings, deliverables, Deloitte, presentations | Kate meeting, equity form, AI roadmap |
| `tech` | OutBot, code, feature, bug, API, deploy | Memory recall, CLI formatting |
| `personal` | Buy, purchase, book, appointment, health | Buy conduit, purchase Cursor |
| `health` | Doctor, medical, screen, appointment, health | Bowel screen, doctor appointment |
| `research` | Research, understand, learn, investigate, read | GLM-5 research, memory upgrade idea |
| `admin` | Form, nomination, paperwork, filing | Equity partner form |

Add to frontmatter: `category: business`

### 4. Generate Actionable Steps
Replace generic steps with specific, actionable ones based on the category and content.

**Rules:**
- Steps should be concrete actions Troy can tick off
- Include phone numbers, URLs, file paths where findable
- Keep to 3-7 steps (ADHD-friendly, not overwhelming)
- First step should be the smallest possible action (reduce activation energy)
- Last step should be "Update status to done" or similar closure

**Examples by category:**

**Personal errand** ("Buy 30mm conduit electrical"):
```markdown
## Steps
- [ ] Check Bunnings stock online for 30mm electrical conduit (need 20m+)
- [ ] Drive to nearest Bunnings or order for delivery
- [ ] Purchase 20m+ of 30mm conduit
- [ ] Load into van
- [ ] Mark as done
```

**Health** ("Book doctor appointment East Bentleigh"):
```markdown
## Steps
- [ ] Call East Bentleigh Medical Centre (look up number)
- [ ] Request next available appointment
- [ ] Confirm date/time and add to calendar
- [ ] Mark as done
```

**Business** ("Kate - Continuous Delivery Meeting"):
```markdown
## Steps
- [ ] Check calendar for next Kate meeting date
- [ ] Review continuous-delivery.md for latest pitch points
- [ ] Prepare 3 key talking points for the meeting
- [ ] Draft any slides/docs needed (use pptx skill if needed)
- [ ] Attend meeting and capture action items
- [ ] Update this task with outcomes
```

**Research** ("GLM-5 research"):
```markdown
## Steps
- [ ] Search for GLM-5 announcements and papers
- [ ] Summarise: what it is, who made it, key capabilities
- [ ] Note relevance to current work (if any)
- [ ] Write summary in description section
- [ ] Mark as done
```

### 5. Validate Eisenhower Classification
Review the current quadrant assignment against actual content:

```python
# Reassess based on enriched understanding
urgent = (
    due_date and days_overdue > 0 or          # Already overdue
    due_date and days_until_due <= 3 or        # Due within 3 days
    category == "health" and "overdue" in title # Health items shouldn't wait
)

important = (
    category in ["business", "health"] or       # Work and health always important
    priority in ["high", "medium"] or            # Explicitly prioritised
    has_real_description                         # Someone took time to describe it
)
```

If classification changes, update the frontmatter fields:
- `eisenhower_quadrant`
- `eisenhower_urgent`
- `eisenhower_important`

### 6. Add Context Links
If related files were found in step 2, add a `## Related` section:
```markdown
## Related
- `continuous-delivery.md` — pitch points for Kate meeting
- `.claude/work/tasks/OUT-245-ai-ppt.md` — related AI presentation task
```

### 7. Update the File
- Replace the generic description with enriched content
- Replace template steps with actionable steps
- Add `category:` to frontmatter
- Add `enriched: true` to frontmatter
- Update `updated:` timestamp
- Add progress log entry: `- YYYY-MM-DD: Enriched by work-item-enricher agent`

### 8. Report Summary
After processing all items:
```
Work Item Enrichment Complete

Enriched: 12 items
- business: 4
- personal: 3
- health: 2
- research: 2
- tech: 1

Reclassified: 3 items (Eisenhower quadrant changed)
Skipped: 5 items (already enriched)

Items needing your input:
- OUT-280: YouTube link needs manual review (can't fetch video)
- OUT-260: "mel hosting" — unclear what this refers to, needs context
```

## Rules
- Never delete existing content — only add or replace generic placeholders
- If the title is ambiguous, flag it for Troy's input rather than guessing
- Use Australian English spelling
- Keep steps ADHD-friendly: short, concrete, low activation energy
- Don't over-enrich — 3-7 steps max, not a project plan
- Add `enriched: true` to frontmatter so we don't re-process
- Preserve all existing frontmatter fields (don't remove reminder_id, source, etc.)

## Skip Conditions
Skip enrichment if:
- File already has `enriched: true` in frontmatter
- Status is `done` (no point enriching completed items)
- File is in `done/` directory

## Dependencies
- **Work Tracker agent**: For file format and ID conventions
- **Web search**: For finding phone numbers, URLs, addresses (when available)
- **Codebase grep**: For finding related files and context
