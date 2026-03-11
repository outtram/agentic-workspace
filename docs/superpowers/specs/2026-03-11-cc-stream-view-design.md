# CC Stream View — Design Spec

**Date:** 2026-03-11
**Status:** Approved
**Author:** Troy + Claude

## Problem

The Command Centre's 9-box grid treats all tasks as equal-sized tiles sorted by Eisenhower quadrant. This doesn't match how Troy works: newest first, unread items demand attention, old stuff fades. 41 tasks across 5 pages means constant paging with no visual signal for what's fresh. The ADHD tax is high — everything looks the same.

## Solution

A new **Stream View** — an inbox-style scrollable list sorted by recency, with visual brightness indicating freshness. Items have three states (NEW, SEEN, BACK) and can be bumped up or down with single keypresses. The existing grid and diagram views remain accessible via `v` to cycle.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Default view | Stream | Matches Troy's "unread + newest" mental model |
| Sort order | Recency (last touched / created) | Most natural for ADHD — fresh stuff on top |
| Categories | Source label only (email/reminder/task) | YAGNI — no tagging system, just origin |
| New item notification | Status bar flash (3s fade) | Option B from brainstorm — low disruption, visible |
| Bump keys | `t` top, `b` back, `s` snooze | No shift keys, easy to remember |
| Chat mode | Split layout (30% stream / 70% chat) | Option A — keeps context visible while chatting |
| View cycling | `v` key: Stream → Grid → Diagram | Grid preserved, not deleted |

## Stream View

### Item States

| State | Symbol | Visual | Position |
|-------|--------|--------|----------|
| NEW | `●` | Bright text, green left border, `NEW` badge | Top of stream |
| SEEN | `○` | Dim text, grey left border | Middle |
| BACK | `◌` | Very dim, 50% opacity, `BACK` badge | Bottom |

- Items enter as NEW when created, imported from email, or synced from reminders
- Opening an item (Enter) auto-marks it as SEEN
- `t` marks as NEW and moves to position #1
- `b` marks as BACK and sinks to bottom
- `s` removes from stream, reappears as NEW after chosen delay (1h / tomorrow / next week)
- `d` marks done (disappears from stream)
- `z` undoes last bump/done action

### Sort Order

Within each state group (NEW → SEEN → BACK), items sort by last-touched timestamp descending. "Last touched" means: created, bumped, opened, or edited — whichever is most recent.

### Item Row Layout

```
[state icon] [badge?] [title                          ] [source label] [relative time]
●            NEW      NotebookLM feature idea           email          2m ago
○                     AI Roadmap                        task           2d ago
◌            BACK     GLM-5 research                    task           1w ago
```

Focused item has orange left border (`#FF6B35`) and `▸` cursor replacing the state icon.

### Source Labels

| Source | Colour | When |
|--------|--------|------|
| `email` | `#FF6B35` (orange) | Imported via email check |
| `reminder` | `#d4aa00` (gold) | Synced from macOS Reminders |
| `task` | `#00D4AA` (green) | Manually created or existing work items |

### Data Model Changes

Add to task YAML frontmatter:

```yaml
stream_state: new | seen | back    # default: new
last_touched: "2026-03-11T10:28:00"  # ISO timestamp
source: email | reminder | task      # origin
snoozed_until: null                  # ISO timestamp or null
```

`last_touched` updates on: creation, bump (t/b), open (Enter), edit, snooze return.

## Right Panel

Same `ContextPanel` widget, showing:

1. **DETAIL** — focused item's full info (title, ID, source, age, description preview)
2. **STREAM** — quick counts: `4 new · 5 seen · 2 back · 0 snoozed · 41 total`
3. **OUTBOT** — last response or "No recent activity"

## Status Bar

### Line 1 (hotkey hints):
```
Enter Open  t Top  b Back  s Snooze  d Done  z Undo  v View  c Chat  / Cmds  : Filter  ? Help
```

### Line 2 (counts):
```
41 items · 4 new · 2 back | TG: ON | BEAT: ON | Stream View
```

## Notification Bar

When new items arrive (via heartbeat polling):
- A notification bar appears at the top of the stream: `✉ 1 new email imported  ⏰ 2 reminders synced`
- Background: `#1a2e1a`, border: `#00D4AA33`
- Auto-fades after 3 seconds
- Does not interrupt current focus position

## Chat Mode (Split Layout)

When user presses `c`:
1. Stream narrows to ~30% width, dims to 30% opacity
2. Chat panel expands to ~70% width
3. "CHATTING ABOUT" header shows focused item (title + ID)
4. Chat messages render with timestamps, role labels, progress steps (⚡)
5. Input field at bottom with "Esc to close" hint
6. Pressing Esc returns to full stream

Chat history persists per session (same as current behaviour).

## Proactive Polling

Add to existing heartbeat cycle (60s):
- **Email check:** `inbox.check(limit=5, unread_only=True)` — import new emails as tasks with `source: email`
- **Reminder sync:** Quick sync (last 24h) — import new reminders with `source: reminder`
- New items appear at top of stream with NEW state
- Status bar notification flashes for 3s

Only runs when heartbeat bridge is ON. No polling if BEAT: OFF.

## View Switching

`v` key cycles through views:

```
Stream → Grid → Diagram → Stream
```

Each view preserves its own state (focus position, selection, etc.). The right panel adapts content per view. Status bar shows current view name.

## Snooze Picker

When user presses `s`:
1. Small inline picker appears below the focused item (or as a Textual modal)
2. Three options: `1` = 1 hour, `2` = tomorrow 9am, `3` = next week Monday 9am
3. Single keypress selects — no confirmation needed
4. Item disappears from stream, `snoozed_until` set in frontmatter
5. Heartbeat checks for expired snoozes each tick, resurfaces as NEW

## New Widget: StreamList

**File:** `brain/command_centre/stream_list.py`

Inherits from `Container` (same pattern as TileGrid and DiagramGrid). Uses Textual's `VerticalScroll` with `Static` widgets for each row — no fixed tile count, renders all items.

### Key methods:
- `update_items(tasks, focus_index, ...)` — re-render all rows
- `set_focus(index)` — move cursor, auto-scroll to keep visible
- `get_focused_task()` — return currently focused task dict

### Navigation:
- `↑` / `↓` — move focus one item
- `Page Up` / `Page Down` — jump 10 items
- `Home` / `End` — jump to top / bottom
- `Enter` — open focused item (switches to TaskFocusView, marks SEEN)

## Implementation Scope

### New files:
- `brain/command_centre/stream_list.py` — StreamList widget
- `brain/command_centre/bump.py` — bump/snooze logic + undo stack

### Modified files:
- `brain/command_centre/app.py` — add stream view mode, `v` key cycling, notification bar, chat split layout
- `brain/command_centre/task_loader.py` — add `stream_state`, `last_touched`, `source` fields
- `brain/command_centre/context_panel.py` — stream counts in right panel, chat split mode
- `brain/command_centre/status_bar.py` — stream-specific hints + counts
- `brain/command_centre/heartbeat_bridge.py` — add email + reminder polling

### Not changed:
- `tile_grid.py` — untouched, still works for grid view
- `diagram_grid.py` — untouched
- `task_focus.py` — untouched (Enter from stream opens same focus view)
- `router.py` — untouched (commands work the same)

## Testing

- Unit tests for bump logic (t/b/s state transitions, sort order, undo)
- Unit tests for stream sort (NEW before SEEN before BACK, recency within groups)
- Unit tests for snooze expiry detection
- Integration test for view cycling (stream → grid → diagram → stream)
- Snapshot tests for stream row rendering
