# Phase 3: Integration Chain Tests

> Prompt for Claude Code — implements cross-module integration tests for Command Centre

## Context

The Command Centre (`brain/command_centre/`) chains multiple modules together:
- **task_loader.py** loads YAML-frontmatter markdown files → Python dicts
- **router.py** parses user input → dispatches to handlers
- **handlers/** mutate task files + today list on disk
- **app.py** orchestrates: load → render → handle input → mutate → re-render

Phase 1 fixed broken tests. Phase 2 added widget-level tests. Phase 3 tests full chains that cross module boundaries — data flows end-to-end.

## Key Modules

```
task_loader.py   load_tasks() → list[dict]
                 load_today_list() → list[str]
                 save_today_list(ids)
                 find_task_file(id) → Path

router.py        Router.route(cmd, selected, focused, tasks, today) → str

handlers/
  triage.py      handle_done(ids), handle_today(ids, today), handle_remove(ids, today), handle_quadrant(q, ids)
  enrich.py      handle_enrich(ids, tasks, claude, progress)
  memory.py      handle_remember(text), handle_forget(text)
  agent_runner.py  handle_agents(args), handle_skills(args)
```

## Tests to Write

### File 1: `brain/tests/test_command_centre/test_task_loader_integration.py`

Test the full task loading pipeline with real markdown files.

**Test class: TestTaskLoading**

1. `test_load_tasks_from_directory` — create a `tmp_path` with 3 valid task markdown files (YAML frontmatter + description body), call `load_tasks(task_dir=tmp_path)`, verify:
   - Returns 3 dicts
   - Each has `id`, `title`, `status`, `eisenhower_quadrant`
   - `_description` field contains the markdown body text

2. `test_tasks_sorted_by_weight` — create tasks with different quadrants (q1, q2, q4), verify q1 sorts first (highest weight)

3. `test_overdue_tasks_get_weight_boost` — create a task with `due_date` in the past, verify it gets a higher weight than a q1 task without a due date

4. `test_today_list_roundtrip` — write a today list with `save_today_list(["OUT-1", "OUT-2"])` to a temp dir, read it back with `load_today_list()`, verify both IDs present

5. `test_find_task_file_locates_file` — create a task file named `OUT-123-some-title.md` in tmp_path, verify `find_task_file("OUT-123")` returns the correct Path

6. `test_find_task_file_returns_none_for_missing` — verify `find_task_file("OUT-NOPE")` returns None

**Fixture helpers:**

```python
def _write_task(tmp_path, task_id, title, quadrant="q2", status="open", due_date=None):
    """Write a minimal task markdown file."""
    meta = {"id": task_id, "title": title, "status": status, "eisenhower_quadrant": quadrant}
    if due_date:
        meta["due_date"] = due_date
    front = yaml.dump(meta, default_flow_style=False)
    body = f"## Description\n\nThis is {title}.\n"
    path = tmp_path / f"{task_id}-{title.lower().replace(' ', '-')}.md"
    path.write_text(f"---\n{front}---\n{body}")
    return path
```

Note: `load_tasks()` and `load_today_list()` read from hard-coded paths under `.claude/work/tasks/` and `.claude/dashboards/today.yml`. You'll need to monkeypatch the module-level constants or use `patch` to redirect the paths to `tmp_path`. Check how `task_loader.py` resolves its paths and patch accordingly.

### File 2: `brain/tests/test_command_centre/test_router_integration.py`

Test the Router routing slash commands through to handlers and getting results back.

**Test class: TestRouterSlashCommands**

7. `test_help_returns_all_sections` — route `/help`, verify output contains "Navigation", "Slash Commands", "Filters", "Focus View"

8. `test_done_with_ids_calls_handler` — mock `RemindersManager`, route `/done` with `selected_ids={"OUT-1"}`, verify `complete_reminder("OUT-1")` called

9. `test_today_adds_and_persists` — route `/today` with `selected_ids={"OUT-1"}`, `today_ids=[]`, verify:
   - Returns "Added 1"
   - `save_today_list` was called
   - `today_ids` now contains "OUT-1"

10. `test_remove_from_today` — start with `today_ids=["OUT-1", "OUT-2"]`, route `/remove` with `selected_ids={"OUT-1"}`, verify:
    - Returns "Removed 1"
    - `today_ids` no longer contains "OUT-1"

11. `test_quadrant_move` — create a real task file in tmp_path, route `/q1` with that task's ID, verify the file's YAML frontmatter now has `eisenhower_quadrant: q1`

12. `test_unknown_command_returns_error` — route `/xyzzy`, verify result contains "Unknown command"

13. `test_aliases_work` — route `/daily-review`, verify it routes to the same handler as `/daily` (both should not crash; mock the actual daily review subprocess)

14. `test_remember_calls_shared_memory` — mock subprocess, route `/remember always use bun`, verify subprocess called with correct args

15. `test_agent_list` — route `/agent`, verify result lists agent names (overseer, work-tracker, etc.)

16. `test_skill_list` — route `/skill`, verify result lists skill names (daily-review, pptx, etc.)

**Test class: TestRouterNaturalLanguage**

17. `test_natural_text_goes_to_outbot` — route "what's on my plate today?" (no `/` prefix), verify it calls the Claude/OutBot path (mock the client, verify `_handle_natural` invoked)

18. `test_filter_prefix_handled` — route `:q1`, verify result indicates filter applied (not treated as unknown command)

### File 3: `brain/tests/test_command_centre/test_triage_chain.py`

Test the full triage chain: handler → file mutation → reload.

**Test class: TestTriageChain**

19. `test_today_add_remove_roundtrip` —
    - Start with empty today list
    - Call `handle_today(["OUT-1", "OUT-2"], today_ids)`
    - Verify both added
    - Call `handle_remove(["OUT-1"], today_ids)`
    - Verify only OUT-2 remains
    - Reload from disk with `load_today_list()`
    - Verify disk state matches in-memory state

20. `test_quadrant_move_updates_file` —
    - Write a task file with `eisenhower_quadrant: q4`
    - Call `handle_quadrant("q1", ["OUT-1"])`
    - Re-read the file, parse YAML
    - Verify `eisenhower_quadrant: q1`, `eisenhower_urgent: true`, `eisenhower_important: true`

21. `test_quadrant_move_preserves_description` —
    - Write a task file with a multi-line description
    - Call `handle_quadrant("q2", [task_id])`
    - Re-read file, verify the description body is unchanged

22. `test_done_marks_completed` —
    - Mock `RemindersManager.complete_reminder`
    - Call `handle_done(["OUT-1", "OUT-2"])`
    - Verify `complete_reminder` called twice
    - Verify return string says "Completed 2"

23. `test_done_handles_partial_failure` —
    - Mock `complete_reminder` to raise on second call
    - Call `handle_done(["OUT-1", "OUT-2"])`
    - Verify return says "Completed 1" (first succeeded, second failed silently)

### File 4: `brain/tests/test_command_centre/test_navigation_chain.py`

Test the navigation stack (drill-in / drill-out) end-to-end in the TUI.

**Test class: TestNavigationStack** (requires app mount)

Use the standard `mock_env` fixture but with parent/child task relationships:

```python
PARENT_TASK = {
    "id": "OUT-P1", "title": "Parent task", "status": "open",
    "eisenhower_quadrant": "q1", "children": ["OUT-C1", "OUT-C2"],
}
CHILD_TASKS = [
    {"id": "OUT-C1", "title": "Child one", "status": "open", "eisenhower_quadrant": "q1", "parent": "OUT-P1"},
    {"id": "OUT-C2", "title": "Child two", "status": "open", "eisenhower_quadrant": "q2", "parent": "OUT-P1"},
]
ALL_TASKS = [PARENT_TASK] + CHILD_TASKS
```

24. `test_enter_on_parent_drills_down` — focus on parent task, press Enter, verify:
    - `app._nav_stack` has one entry
    - Grid now shows only child tasks

25. `test_escape_pops_nav_stack` — drill into parent, press Escape, verify:
    - `app._nav_stack` is empty
    - Grid shows all top-level tasks again

26. `test_enter_on_leaf_opens_focus` — focus on a child task (no children), press Enter, verify `app._view_mode == "focus"`

27. `test_double_escape_flow` — enter focus view on a child, press Escape (back to grid showing children), press Escape again (back to top-level grid), verify `app._view_mode == "grid"` and `app._nav_stack` is empty

### File 5: `brain/tests/test_command_centre/test_filter_chain.py`

Test the filter → grid refresh chain.

**Test class: TestFilterChain** (requires app mount)

28. `test_quadrant_filter_shows_matching` — apply q1 filter via `:q1` in command bar, verify only q1 tasks visible in the tile grid

29. `test_today_filter_shows_today_only` — add a task to today, apply `:today` filter, verify only today tasks shown

30. `test_overdue_filter` — create a task with past due_date, apply `:overdue`, verify it appears

31. `test_clear_filter_shows_all` — apply a filter, then apply `:all` or press Escape, verify all tasks visible again

32. `test_search_filter` — apply `:search banana`, verify only tasks with "banana" in title/description shown

## Guidelines

- Mark integration tests with `@pytest.mark.integration`
- Use `tmp_path` for all file I/O — never touch real task files
- Monkeypatch file paths in `task_loader.py` to point at `tmp_path`
- Mock external dependencies: `RemindersManager`, `ClaudeClient`, subprocess calls
- Test real file I/O (write → read → verify) — that's the point of integration tests
- Each test should be independent — no shared mutable state between tests
- Don't test UI appearance (colours, exact markup) — test data flow correctness
- Verify with: `python3 -m pytest brain/tests/test_command_centre/ -x -q`
- All tests must pass alongside existing tests (282+ currently passing)

## Verification

```bash
# Syntax check
python3 -m py_compile brain/tests/test_command_centre/test_task_loader_integration.py
python3 -m py_compile brain/tests/test_command_centre/test_router_integration.py
python3 -m py_compile brain/tests/test_command_centre/test_triage_chain.py
python3 -m py_compile brain/tests/test_command_centre/test_navigation_chain.py
python3 -m py_compile brain/tests/test_command_centre/test_filter_chain.py

# Run integration tests only
python3 -m pytest brain/tests/test_command_centre/ -m integration -x -q

# Run full suite
python3 -m pytest brain/tests/ -q
```

Expected: 32 new tests + 316 from Phase 1+2 = 348+ total, all passing.
