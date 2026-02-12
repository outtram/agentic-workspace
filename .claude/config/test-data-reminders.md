# Test Data: Eisenhower Matrix Reminders

> Comprehensive test dataset for reminders-importer and dashboard-generator agents

**List:** `EISENHOWER_TEST`
**Created:** 2026-02-12
**Total reminders:** 17 active + 1 completed (skipped)

---

## Q1: Urgent & Important (Expected: 4 tasks)

| Title | Priority | Due Date | Body | Expected Classification |
|-------|----------|----------|------|------------------------|
| Fix critical production bug | 1 (high) | 2026-02-12 (today) | Yes | Q1 - urgent (today) + important (P1) |
| Complete security audit report | 1 (high) | 2026-02-13 (tomorrow) | Yes | Q1 - urgent (tomorrow) + important (P1) |
| Submit client proposal | 5 (medium) | 2026-02-14 (2 days) | Yes | Q1 - urgent (≤3 days) + important (P5) |
| Review and merge pending PR | 1 (high) | 2026-02-11 (OVERDUE) | Yes | Q1 - urgent (overdue) + important (P1) |

---

## Q2: Important but Not Urgent (Expected: 4 tasks)

| Title | Priority | Due Date | Body | Expected Classification |
|-------|----------|----------|------|------------------------|
| Prepare Q1 performance reviews | 1 (high) | 2026-02-19 (7 days) | Yes | Q2 - not urgent (>3 days) + important (P1) |
| Refactor authentication module | 5 (medium) | 2026-02-26 (14 days) | Yes | Q2 - not urgent + important (P5) |
| Update team documentation | 5 (medium) | 2026-02-22 (10 days) | Yes | Q2 - not urgent + important (P5) |
| Renew SSL certificates | 9 (low) | 2026-03-14 (30 days) | Yes | Q2 - not urgent + important (has due date) |

---

## Q3: Urgent but Not Important (Expected: 3 tasks)

| Title | Priority | Due Date | Body | Expected Classification |
|-------|----------|----------|------|------------------------|
| Respond to newsletter survey | 0 (none) | 2026-02-13 (tomorrow) | No | Q3 - urgent (tomorrow) + not important (no P, no body) |
| RSVP to company social event | 9 (low) | 2026-02-14 (2 days) | No | Q3 - urgent (≤3 days) + not important (low P, no body) |
| Water office plants | 0 (none) | 2026-02-12 (today) | No | Q3 - urgent (today) + not important (no P, no body) |

---

## Q4: Not Urgent & Not Important (Expected: 3 tasks)

| Title | Priority | Due Date | Body | Expected Classification |
|-------|----------|----------|------|------------------------|
| Organize digital files | 0 (none) | None | No | Q4 - not urgent (no due) + not important (no P, no body) |
| Read interesting article about AI | 0 (none) | 2026-03-29 (45 days) | No | Q4 - not urgent (far out) + not important (no P) |
| Clean out old browser bookmarks | 0 (none) | None | Yes (short) | Q4 - not urgent (no due) + not important (no P) |

---

## Edge Cases (Expected: 3 tasks imported, 1 skipped)

| Title | Priority | Due Date | Test Case | Expected Behavior |
|-------|----------|----------|-----------|-------------------|
| 🚀 Deploy new feature to staging | 5 (medium) | 2026-02-13 (tomorrow) | Emoji in title | Q1 - emoji removed from filename |
| Investigate performance degradation... | 1 (high) | 2026-02-13 (tomorrow) | Very long title (84 chars) | Q1 - title truncated to 50 chars in filename |
| Fix: "Can't save" error (Windows/macOS) | 1 (high) | 2026-02-12 (today) | Special characters | Q1 - special chars escaped/removed |
| This reminder is already completed | 1 (high) | None | Completed = true | **SKIPPED** - should not be imported |

---

## Classification Logic Reference

**Urgent:** `due_date_within_3_days OR priority == 1`
**Important:** `priority in [1-5] OR has_body OR has_due_date`

**Quadrant Assignment:**
- Q1: Urgent AND Important
- Q2: NOT Urgent AND Important
- Q3: Urgent AND NOT Important
- Q4: NOT Urgent AND NOT Important

---

## Expected Import Results

- **Total imported:** 17 tasks (1 completed reminder skipped)
- **Q1 (Do First):** 7 tasks (4 standard + 3 edge cases)
- **Q2 (Schedule):** 4 tasks
- **Q3 (Delegate):** 3 tasks
- **Q4 (Eliminate):** 3 tasks

---

## Testing Checklist

### Import Test
- [ ] All 17 active reminders imported
- [ ] 1 completed reminder skipped
- [ ] Unique OUT-2XX IDs generated
- [ ] No duplicate imports on second run
- [ ] Frontmatter fields populated correctly
- [ ] Classification matches expected quadrants
- [ ] Emoji removed from filenames
- [ ] Long titles truncated
- [ ] Special characters handled

### Dashboard Test
- [ ] All 17 tasks visible in dashboard
- [ ] Tasks grouped by correct quadrant
- [ ] Color coding correct (red/blue/yellow/gray)
- [ ] Due dates formatted correctly
- [ ] "From Reminders" badge visible
- [ ] Overdue task highlighted
- [ ] Filter buttons work (Reminders Only, Show All)
- [ ] Task cards expand/collapse
- [ ] Dark mode toggles correctly

### Cleanup Utility Commands
```bash
# Delete test list and all reminders
osascript -e 'tell application "Reminders" to delete list "EISENHOWER_TEST"'

# Delete imported task files (after testing)
rm .claude/work/tasks/OUT-2*-*.md

# Delete generated dashboards (after testing)
rm .claude/dashboards/eisenhower-*.html
```

---

## Maintenance Commands

**View test reminders:**
```bash
osascript -e 'tell application "Reminders" to get name of every reminder of list "EISENHOWER_TEST"'
```

**Add more test reminders:**
```bash
osascript -e 'tell application "Reminders"
    tell list "EISENHOWER_TEST"
        make new reminder with properties {name:"New test task", priority:1}
    end tell
end tell'
```

**Complete a test reminder:**
```bash
osascript -e 'tell application "Reminders"
    set r to first reminder of list "EISENHOWER_TEST" whose name is "Fix critical production bug"
    set completed of r to true
end tell'
```

**Recreate test data:**
Run the commands from this session to recreate all test reminders from scratch.

---

**Last updated:** 2026-02-12
**Purpose:** Comprehensive testing of macOS Reminders → Eisenhower Matrix integration
