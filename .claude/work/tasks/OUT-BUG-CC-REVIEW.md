---
id: OUT-BUG-CC-REVIEW
title: Command Centre bug fixes from fresh review
type: task
status: todo
priority: high
category: tech
eisenhower_quadrant: q1
eisenhower_urgent: true
eisenhower_important: true
created: 2026-02-28
assignee: Claude Code
updated: '2026-03-23'
enriched: true
---

# Command Centre Bug Fixes — Fresh Review (28 Feb 2026)

## Description
Address the six Command Centre issues identified in the fresh review, prioritising the today-list data loss risk and the missing configurable chat toggle first.

6 issues found across the 30-file Command Centre codebase. All files pass syntax checks. No import errors. Issues are ordered by severity.

---

## BUG 1 (HIGH): Today list only saved on quit — data loss risk

**Problem:** `save_today_list()` is only called once in the entire codebase — inside `app.py` line 656, in the escape-quit handler. But `self.today_ids` is mutated in at least 4 other places without saving:

- `app.py` → `_add_to_today()` (~line 1170) — adds/removes items, never saves
- `app.py` → `_mark_done()` (~line 1147) — removes completed tasks from today, never saves
- `app.py` → `_accept_predictions()` (~line 1300) — adds predicted tasks, never saves
- `handlers/triage.py` → `handle_today()` and `handle_remove()` — mutate the list passed by reference, never save

**Impact:** If the app crashes, gets killed, terminal closes, or system loses power, ALL today list changes since launch are lost.

**Fix:** Add `save_today_list(self.today_ids)` after every mutation of `self.today_ids`. Specifically:
1. End of `_add_to_today()` — before `self._refresh_all()`
2. End of `_mark_done()` — before `self._refresh_all()`
3. End of `_accept_predictions()` — before `self._refresh_all()`
4. After the router returns in `on_input_submitted()` (~line 907) where `self.today_ids = load_today_list()` already reloads — this path is fine since triage handlers mutate in-place. But add a `save_today_list(self.today_ids)` call after the `result = await self.router.route(...)` block completes for slash commands that modify today (or just save unconditionally — it's a cheap YAML write).

The import `save_today_list` is already at the top of `app.py` (line 38).

---

## BUG 2 (MEDIUM): Missing `chat_toggle` hotkey default in config_loader.py

**Problem:** `app.py` uses `hk.get("chat_toggle", "c")` in both `_handle_grid_key()` (line 489) and `_handle_focus_key()` (line 535). But `config_loader.py`'s `_DEFAULTS["hotkeys"]` dict does not include a `chat_toggle` entry.

The fallback `"c"` means the key works, but it's invisible to anyone trying to customise hotkeys via `.claude/config/command-centre.yml`.

**Fix:** Add `"chat_toggle": "c"` to the `_DEFAULTS["hotkeys"]` dict in `brain/command_centre/config_loader.py` (after `"action_menu": "x"` on line 23).

---

## BUG 3 (LOW): `/help` command crashes if help_data.yml is missing or corrupt

**Problem:** In `router.py` line 137-138:
```python
from .help_gen import generate_help_router, _load_yaml, HELP_DATA
return generate_help_router(_load_yaml(HELP_DATA))
```
`_load_yaml()` calls `path.read_text()` with no try/except. If `help_data.yml` is deleted or has invalid YAML, the `/help` command crashes with an unhandled exception instead of returning a friendly error.

**Fix:** Wrap in try/except in `router.py`:
```python
elif cmd == "/help":
    try:
        from .help_gen import generate_help_router, _load_yaml, HELP_DATA
        return generate_help_router(_load_yaml(HELP_DATA))
    except Exception:
        return "[red]Help data unavailable[/]"
```

---

## BUG 4 (LOW): Duplicate entry in command palette

**Problem:** `brain/command_centre/command_palette.py` lines 28 and 33 both list email import:
```python
("/import", "Import unread emails as tasks"),
("/import-emails", "Import unread emails as tasks"),
```
These route to the same handler. The palette shows both, which is noisy.

**Fix:** Remove the `/import-emails` line (line 33). Keep `/import` as the canonical command. The alias still works if typed manually — this just declutters the palette.

---

## BUG 5 (COSMETIC): `_mark_done()` blocks the TUI synchronously

**Problem:** `app.py`'s `_mark_done()` method (~line 1117) calls `RemindersManager().complete_reminder()` synchronously for each task in a loop. If RemindersManager does file I/O or iOS sync, the TUI freezes until all tasks are processed.

The slash command version (`/done` via `handlers/triage.py`) has the same issue — it's declared `async def` but doesn't actually `await` anything async inside.

**Fix (future):** Wrap the blocking calls in `asyncio.get_running_loop().run_in_executor(None, ...)` to keep the TUI responsive. This is a nice-to-have, not urgent — the current blocking is brief for small task counts.

---

## BUG 6 (COSMETIC): Agent/skill data duplicated in 3 files

**Problem:** Agent and skill lists are independently defined in:
1. `brain/command_centre/handlers/agent_runner.py` — `_AGENTS` and `_SKILLS` dicts
2. `brain/command_centre/skill_matcher.py` — `_AGENT_SUGGESTIONS` and `_SKILL_SUGGESTIONS` dicts
3. `brain/command_centre/command_palette.py` — `_AGENTS` and `_SKILLS` tuples

Adding a new agent or skill requires updating all three files.

**Fix (future):** Extract a single `_registry.py` or YAML file that all three modules read from. Not urgent but prevents drift.

---

## Verification after fixes

After applying fixes, run:
```bash
cd /Users/touttram/CODE/AAGLOBAL
python3 -m py_compile brain/command_centre/app.py
python3 -m py_compile brain/command_centre/config_loader.py
python3 -m py_compile brain/command_centre/router.py
python3 -m py_compile brain/command_centre/command_palette.py
```

Then launch `cc` and test:
1. Add a task to today → kill terminal → relaunch → confirm task is still in today list (Bug 1)
2. Check `c` key toggles chat in both grid and focus views (Bug 2)
3. Type `/help` in the command bar (Bug 3)
4. Open command palette with `/` and confirm no duplicate import entries (Bug 4)

## Progress Log
- 2026-03-23: Enriched in batch review. Preserved existing detail and replaced placeholders where needed.
