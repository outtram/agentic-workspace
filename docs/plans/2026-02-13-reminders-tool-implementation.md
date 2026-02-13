# Reminders Management Tool - Implementation Plan (Phase 1)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build core foundation for bi-directional reminder sync - Python API, AppleScript adapter, work item I/O, and basic CLI.

**Architecture:** Event-driven system with RemindersManager as public API, AppleScript adapter for Reminders.app integration, file-based work item storage, and pluggable CLI interface.

**Tech Stack:** Python 3.11+, pytest, click (CLI), PyYAML (frontmatter), python-dateutil (date parsing)

---

## Phase 1 Overview

This phase implements the core foundation (v0.1):
- ✅ Data models (WorkItem, Reminder, Events)
- ✅ Event bus (pub/sub system)
- ✅ AppleScript adapter (read/write Reminders.app)
- ✅ Work item file I/O (YAML frontmatter + markdown)
- ✅ Basic RemindersManager API
- ✅ Simple CLI (add, list, complete, delete)
- ✅ Unit tests (80%+ coverage)

**Estimated Time:** 8-12 hours over 3-4 sessions

---

## Setup & Project Structure

### Task 0: Project Scaffold

**Files:**
- Create: `.claude/reminders/README.md`
- Create: `.claude/reminders/pyproject.toml`
- Create: `.claude/reminders/setup.py`
- Create: `.claude/reminders/requirements.txt`
- Create: `.claude/reminders/requirements-dev.txt`

**Step 1: Create project structure**

```bash
cd /Users/touttram/CODE/AAGLOBAL
mkdir -p .claude/reminders/{core,adapters,sync,enrichment,plugins,hooks,tests/{unit,integration,e2e,fixtures}}
touch .claude/reminders/{core,adapters,sync,enrichment,plugins,hooks,tests}/__init__.py
```

**Step 2: Create pyproject.toml**

```toml
[project]
name = "reminders-manager"
version = "0.1.0"
description = "Bi-directional sync between macOS Reminders and file-native tasks"
authors = [{name = "Troy Outtram"}]
requires-python = ">=3.11"
dependencies = [
    "click>=8.1.0",
    "pyyaml>=6.0",
    "python-dateutil>=2.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.11.0",
]

[project.scripts]
reminder = "reminders.plugins.cli:main"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"
```

**Step 3: Create requirements files**

```bash
# requirements.txt
echo "click>=8.1.0
pyyaml>=6.0
python-dateutil>=2.8.0" > .claude/reminders/requirements.txt

# requirements-dev.txt
echo "pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0" > .claude/reminders/requirements-dev.txt
```

**Step 4: Create README**

```markdown
# Reminders Manager

Bi-directional sync between macOS Reminders.app and file-native task system.

## Installation

```bash
cd .claude/reminders
pip install -e ".[dev]"
```

## Usage

```bash
# Add reminder
reminder add "Call Leon" --due tomorrow --tag phone

# List reminders
reminder list

# Complete reminder
reminder complete OUT-264

# Sync with Reminders.app
reminder sync
```

## Development

```bash
# Run tests
pytest tests/ -v --cov

# Run specific test
pytest tests/unit/test_models.py::test_work_item_creation -v
```

## Architecture

See `docs/plans/2026-02-13-reminders-tool-design.md` for full design.
```

**Step 5: Install dependencies**

```bash
cd .claude/reminders
pip install -e ".[dev]"
```

Expected: Successfully installed reminders-manager and dependencies

**Step 6: Commit**

```bash
git add .claude/reminders/
git commit -m "feat(reminders): initial project scaffold

- Add project structure
- Add pyproject.toml with dependencies
- Add README with usage instructions

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 1: Data Models

**Files:**
- Create: `.claude/reminders/core/models.py`
- Create: `.claude/reminders/tests/unit/test_models.py`

**Step 1: Write failing test for WorkItem**

```python
# .claude/reminders/tests/unit/test_models.py
from datetime import datetime
from reminders.core.models import WorkItem

def test_work_item_creation():
    """Should create WorkItem with all fields"""
    work_item = WorkItem(
        id="OUT-264",
        title="Call Leon",
        status="todo",
        priority="high",
        due_date="2026-02-14",
        tags=["phone", "urgent"],
        tag_categories={"context": ["phone"], "priority": ["urgent"]},
        eisenhower_quadrant="q1",
        eisenhower_urgent=True,
        eisenhower_important=True,
        source="reminder",
        reminder_id="x-apple-reminder://ABC123",
        reminder_list="Reminders",
        description="Discuss equity partner timeline",
        updated=datetime.now()
    )

    assert work_item.id == "OUT-264"
    assert work_item.title == "Call Leon"
    assert "phone" in work_item.tags
    assert work_item.eisenhower_quadrant == "q1"
```

**Step 2: Run test to verify it fails**

```bash
cd .claude/reminders
pytest tests/unit/test_models.py::test_work_item_creation -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'reminders.core.models'"

**Step 3: Write minimal implementation**

```python
# .claude/reminders/core/models.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class WorkItem:
    """Represents a work item (task/bug) in the file-native system"""
    id: str
    title: str
    status: str = "todo"
    priority: str = "low"
    due_date: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    tag_categories: dict[str, list[str]] = field(default_factory=dict)
    eisenhower_quadrant: str = "q4"
    eisenhower_urgent: bool = False
    eisenhower_important: bool = False
    source: str = "manual"
    reminder_id: Optional[str] = None
    reminder_list: Optional[str] = None
    branch: Optional[str] = None
    description: str = ""
    steps: list[str] = field(default_factory=list)
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    def __post_init__(self):
        """Generate branch name if not provided"""
        if not self.branch and self.id:
            # Clean title for branch name
            clean_title = self.title.lower()[:30].replace(" ", "-")
            self.branch = f"task/{self.id}-{clean_title}"

@dataclass
class Reminder:
    """Represents a reminder from Reminders.app via AppleScript"""
    id: str
    name: str
    body: str = ""
    tags: list[str] = field(default_factory=list)
    due_date: Optional[datetime] = None
    priority: int = 0  # 0=none, 1=high, 5=medium, 9=low
    list_name: str = "Reminders"
    completed: bool = False
    modified: Optional[datetime] = None
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_models.py::test_work_item_creation -v
```

Expected: PASS

**Step 5: Add test for Reminder model**

```python
# Append to test_models.py
from reminders.core.models import Reminder

def test_reminder_creation():
    """Should create Reminder with all fields"""
    reminder = Reminder(
        id="x-apple-reminder://ABC123",
        name="Call Leon",
        body="Discuss equity partner timeline",
        tags=["phone", "urgent"],
        due_date=datetime(2026, 2, 14),
        priority=1,
        list_name="Reminders",
        completed=False
    )

    assert reminder.id == "x-apple-reminder://ABC123"
    assert reminder.name == "Call Leon"
    assert reminder.priority == 1
    assert not reminder.completed
```

**Step 6: Run test**

```bash
pytest tests/unit/test_models.py::test_reminder_creation -v
```

Expected: PASS (already implemented in Step 3)

**Step 7: Commit**

```bash
git add .claude/reminders/core/models.py .claude/reminders/tests/unit/test_models.py
git commit -m "feat(reminders): add WorkItem and Reminder data models

- Add WorkItem dataclass with all fields
- Add Reminder dataclass for Reminders.app data
- Add unit tests for both models
- Auto-generate branch name from work item ID

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Event System

**Files:**
- Create: `.claude/reminders/core/events.py`
- Create: `.claude/reminders/tests/unit/test_events.py`

**Step 1: Write failing test for Event base class**

```python
# .claude/reminders/tests/unit/test_events.py
from reminders.core.events import Event, WorkItemCreated, EventBus

def test_event_creation():
    """Should create event with timestamp"""
    event = WorkItemCreated(work_item_id="OUT-264", reminder_id=None)

    assert event.work_item_id == "OUT-264"
    assert event.reminder_id is None
    assert event.timestamp is not None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_events.py::test_event_creation -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal Event implementation**

```python
# .claude/reminders/core/events.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Type
from collections import defaultdict

@dataclass
class Event:
    """Base event class"""
    timestamp: datetime = field(default_factory=datetime.now)

# Work Item Events
@dataclass
class WorkItemCreated(Event):
    work_item_id: str
    reminder_id: Optional[str] = None

@dataclass
class WorkItemUpdated(Event):
    work_item_id: str
    changes: dict = field(default_factory=dict)

@dataclass
class WorkItemCompleted(Event):
    work_item_id: str

@dataclass
class WorkItemDeleted(Event):
    work_item_id: str

# Reminder Events
@dataclass
class ReminderPushed(Event):
    work_item_id: str
    reminder_id: str
    success: bool

@dataclass
class ReminderPulled(Event):
    reminder_id: str
    work_item_id: Optional[str] = None

# Sync Events
@dataclass
class SyncStarted(Event):
    sync_type: str  # "push" | "pull" | "full"

@dataclass
class SyncCompleted(Event):
    pushed: int = 0
    pulled: int = 0
    conflicts: int = 0

@dataclass
class ConflictDetected(Event):
    work_item_id: str
    reminder_id: str
    work_item_modified: Optional[datetime] = None
    reminder_modified: Optional[datetime] = None

@dataclass
class ConflictResolved(Event):
    work_item_id: str
    resolution: str  # "work_item_wins" | "reminder_wins" | "manual_merge"

# Enrichment Events
@dataclass
class EnrichmentSuggested(Event):
    work_item_id: str
    suggestions: dict = field(default_factory=dict)

@dataclass
class EnrichmentApplied(Event):
    work_item_id: str
    applied: dict = field(default_factory=dict)
```

**Step 4: Run test**

```bash
pytest tests/unit/test_events.py::test_event_creation -v
```

Expected: PASS

**Step 5: Write failing test for EventBus**

```python
# Append to test_events.py
def test_event_bus_subscribe_and_publish():
    """Should call handler when event published"""
    bus = EventBus()
    called = []

    def handler(event):
        called.append(event)

    bus.subscribe(WorkItemCreated, handler)
    event = WorkItemCreated(work_item_id="OUT-264")
    bus.publish(event)

    assert len(called) == 1
    assert called[0].work_item_id == "OUT-264"

def test_event_bus_multiple_subscribers():
    """Should call all subscribers for event type"""
    bus = EventBus()
    calls = {"handler1": 0, "handler2": 0}

    def handler1(event):
        calls["handler1"] += 1

    def handler2(event):
        calls["handler2"] += 1

    bus.subscribe(WorkItemCreated, handler1)
    bus.subscribe(WorkItemCreated, handler2)
    bus.publish(WorkItemCreated(work_item_id="OUT-264"))

    assert calls["handler1"] == 1
    assert calls["handler2"] == 1
```

**Step 6: Run test to verify it fails**

```bash
pytest tests/unit/test_events.py::test_event_bus_subscribe_and_publish -v
```

Expected: FAIL with "NameError: name 'EventBus' is not defined"

**Step 7: Implement EventBus**

```python
# Append to .claude/reminders/core/events.py

class EventBus:
    """Simple pub/sub event bus"""

    def __init__(self):
        self._subscribers: dict[Type[Event], list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: Type[Event], handler: Callable):
        """Subscribe handler to event type"""
        self._subscribers[event_type].append(handler)

    def publish(self, event: Event):
        """Publish event to all subscribers"""
        for handler in self._subscribers[type(event)]:
            handler(event)

    def unsubscribe(self, event_type: Type[Event], handler: Callable):
        """Unsubscribe handler from event type"""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
```

**Step 8: Run all event tests**

```bash
pytest tests/unit/test_events.py -v
```

Expected: All PASS

**Step 9: Commit**

```bash
git add .claude/reminders/core/events.py .claude/reminders/tests/unit/test_events.py
git commit -m "feat(reminders): add event system with pub/sub bus

- Add Event base class with timestamp
- Add WorkItem events (Created, Updated, Completed, Deleted)
- Add Reminder events (Pushed, Pulled)
- Add Sync events (Started, Completed, Conflict)
- Add Enrichment events (Suggested, Applied)
- Add EventBus with subscribe/publish/unsubscribe
- Add comprehensive unit tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: AppleScript Adapter

**Files:**
- Create: `.claude/reminders/adapters/applescript.py`
- Create: `.claude/reminders/tests/unit/test_applescript.py`
- Create: `.claude/reminders/tests/fixtures/mock_applescript.py`

**Step 1: Write mock AppleScript adapter for testing**

```python
# .claude/reminders/tests/fixtures/mock_applescript.py
from datetime import datetime
from typing import Optional

class MockAppleScriptAdapter:
    """Mock Reminders.app for testing without real app"""

    def __init__(self):
        self.reminders: dict[str, dict] = {}
        self.call_log: list[tuple] = []
        self._next_id = 1

    def create_reminder(
        self,
        name: str,
        body: str = "",
        tags: Optional[list[str]] = None,
        due_date: Optional[str] = None,
        priority: int = 0,
        list_name: str = "Reminders"
    ) -> str:
        """Create reminder and return ID"""
        reminder_id = f"mock-reminder-{self._next_id}"
        self._next_id += 1

        self.reminders[reminder_id] = {
            "id": reminder_id,
            "name": name,
            "body": body,
            "tags": tags or [],
            "due_date": due_date,
            "priority": priority,
            "list": list_name,
            "completed": False,
            "modified": datetime.now()
        }

        self.call_log.append(("create", name, list_name))
        return reminder_id

    def update_reminder(self, reminder_id: str, **changes):
        """Update reminder fields"""
        if reminder_id not in self.reminders:
            raise ValueError(f"Reminder {reminder_id} not found")

        self.reminders[reminder_id].update(changes)
        self.reminders[reminder_id]["modified"] = datetime.now()
        self.call_log.append(("update", reminder_id))

    def delete_reminder(self, reminder_id: str):
        """Delete reminder"""
        if reminder_id not in self.reminders:
            raise ValueError(f"Reminder {reminder_id} not found")

        del self.reminders[reminder_id]
        self.call_log.append(("delete", reminder_id))

    def fetch_all_reminders(self) -> list[dict]:
        """Fetch all active reminders"""
        self.call_log.append(("fetch_all",))
        return [r for r in self.reminders.values() if not r["completed"]]

    def get_reminder(self, reminder_id: str) -> Optional[dict]:
        """Get single reminder by ID"""
        return self.reminders.get(reminder_id)
```

**Step 2: Write failing test for AppleScript adapter**

```python
# .claude/reminders/tests/unit/test_applescript.py
import pytest
from reminders.adapters.applescript import AppleScriptAdapter
from reminders.tests.fixtures.mock_applescript import MockAppleScriptAdapter

def test_create_reminder():
    """Should create reminder via AppleScript"""
    adapter = MockAppleScriptAdapter()

    reminder_id = adapter.create_reminder(
        name="Call Leon",
        body="Discuss equity partner",
        tags=["phone", "urgent"],
        due_date="2026-02-14",
        priority=1,
        list_name="Reminders"
    )

    assert reminder_id.startswith("mock-reminder-")
    assert len(adapter.call_log) == 1
    assert adapter.call_log[0] == ("create", "Call Leon", "Reminders")

    # Verify reminder stored
    reminder = adapter.get_reminder(reminder_id)
    assert reminder["name"] == "Call Leon"
    assert "phone" in reminder["tags"]

def test_fetch_all_reminders():
    """Should fetch all active reminders"""
    adapter = MockAppleScriptAdapter()

    adapter.create_reminder("Task 1")
    adapter.create_reminder("Task 2")

    reminders = adapter.fetch_all_reminders()
    assert len(reminders) == 2
```

**Step 3: Run test**

```bash
pytest tests/unit/test_applescript.py -v
```

Expected: PASS (mock adapter already implemented)

**Step 4: Implement real AppleScript adapter**

```python
# .claude/reminders/adapters/applescript.py
import subprocess
import re
from datetime import datetime
from typing import Optional

class AppleScriptAdapter:
    """Interface to macOS Reminders.app via AppleScript"""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout

    def create_reminder(
        self,
        name: str,
        body: str = "",
        tags: Optional[list[str]] = None,
        due_date: Optional[str] = None,
        priority: int = 0,
        list_name: str = "Reminders"
    ) -> str:
        """Create reminder and return Apple reminder ID"""
        tags_str = ", ".join(f'"{tag}"' for tag in (tags or []))

        # Build AppleScript
        script = f'''
tell application "Reminders"
    tell list "{list_name}"
        set newReminder to make new reminder
        set name of newReminder to "{self._escape(name)}"
        set body of newReminder to "{self._escape(body)}"
        set priority of newReminder to {priority}
        '''

        if tags:
            script += f'set tags of newReminder to {{{tags_str}}}\n'

        if due_date:
            script += f'set due date of newReminder to date "{due_date}"\n'

        script += '''
        return id of newReminder
    end tell
end tell
'''

        result = self._execute(script)
        return result.strip()

    def update_reminder(self, reminder_id: str, **changes):
        """Update reminder fields"""
        # Build update script based on changes
        updates = []

        if "name" in changes:
            updates.append(f'set name of theReminder to "{self._escape(changes["name"])}"')

        if "body" in changes:
            updates.append(f'set body of theReminder to "{self._escape(changes["body"])}"')

        if "tags" in changes:
            tags_str = ", ".join(f'"{tag}"' for tag in changes["tags"])
            updates.append(f'set tags of theReminder to {{{tags_str}}}')

        if "priority" in changes:
            updates.append(f'set priority of theReminder to {changes["priority"]}')

        if "completed" in changes:
            updates.append(f'set completed of theReminder to {str(changes["completed"]).lower()}')

        script = f'''
tell application "Reminders"
    set theReminder to reminder id "{reminder_id}"
    {chr(10).join(updates)}
end tell
'''

        self._execute(script)

    def delete_reminder(self, reminder_id: str):
        """Delete reminder"""
        script = f'''
tell application "Reminders"
    delete reminder id "{reminder_id}"
end tell
'''
        self._execute(script)

    def fetch_all_reminders(self) -> list[dict]:
        """Fetch all active (non-completed) reminders"""
        script = '''
tell application "Reminders"
    set output to ""
    repeat with aList in lists
        set listName to name of aList
        repeat with aReminder in reminders of aList
            if completed of aReminder is false then
                set rId to id of aReminder
                set rName to name of aReminder
                try
                    set rBody to body of aReminder
                on error
                    set rBody to ""
                end try
                try
                    set rDueDate to due date of aReminder as string
                on error
                    set rDueDate to ""
                end try
                set rPriority to priority of aReminder
                try
                    set rTags to tags of aReminder
                    set tagStr to ""
                    repeat with aTag in rTags
                        if tagStr is "" then
                            set tagStr to aTag
                        else
                            set tagStr to tagStr & "," & aTag
                        end if
                    end repeat
                on error
                    set tagStr to ""
                end try
                set output to output & listName & "|" & rId & "|" & rName & "|" & rBody & "|" & rDueDate & "|" & rPriority & "|" & tagStr & linefeed
            end if
        end repeat
    end repeat
    return output
end tell
'''

        result = self._execute(script)
        return self._parse_reminders(result)

    def _execute(self, script: str) -> str:
        """Execute AppleScript and return output"""
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"AppleScript error: {result.stderr}")

            return result.stdout
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"AppleScript timed out after {self.timeout}s")

    def _escape(self, text: str) -> str:
        """Escape quotes in text for AppleScript"""
        return text.replace('"', '\\"')

    def _parse_reminders(self, output: str) -> list[dict]:
        """Parse pipe-delimited reminder data"""
        reminders = []

        for line in output.strip().split('\n'):
            if not line:
                continue

            parts = line.split('|')
            if len(parts) != 7:
                continue

            list_name, rid, name, body, due_date, priority, tags = parts

            reminders.append({
                "id": rid,
                "name": name,
                "body": body,
                "tags": tags.split(',') if tags else [],
                "due_date": self._parse_date(due_date),
                "priority": int(priority),
                "list": list_name,
                "completed": False,
                "modified": datetime.now()  # AppleScript doesn't expose modified date
            })

        return reminders

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse AppleScript date string to YYYY-MM-DD"""
        if not date_str or date_str == "missing value":
            return None

        try:
            # "Thursday, 12 February 2026 at 12:00:00 am"
            parts = date_str.split(" at ")[0]
            date_obj = datetime.strptime(parts, "%A, %d %B %Y")
            return date_obj.date().isoformat()
        except:
            return None
```

**Step 5: Commit**

```bash
git add .claude/reminders/adapters/applescript.py \
        .claude/reminders/tests/unit/test_applescript.py \
        .claude/reminders/tests/fixtures/mock_applescript.py
git commit -m "feat(reminders): add AppleScript adapter for Reminders.app

- Add real AppleScript adapter with create/update/delete/fetch
- Add mock adapter for testing
- Parse pipe-delimited reminder data from AppleScript
- Handle tags, due dates, priority, completion status
- Add timeout and error handling

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Work Item File I/O

**Files:**
- Create: `.claude/reminders/adapters/workitems.py`
- Create: `.claude/reminders/tests/unit/test_workitems.py`

**Step 1: Write failing test for work item creation**

```python
# .claude/reminders/tests/unit/test_workitems.py
import pytest
from pathlib import Path
from datetime import datetime
from reminders.adapters.workitems import WorkItemFileAdapter
from reminders.core.models import WorkItem

@pytest.fixture
def temp_work_dir(tmp_path):
    """Create temporary work directory"""
    work_dir = tmp_path / "work" / "tasks"
    work_dir.mkdir(parents=True)
    return work_dir

def test_create_work_item_file(temp_work_dir):
    """Should create work item markdown file with YAML frontmatter"""
    adapter = WorkItemFileAdapter(work_dir=temp_work_dir)

    work_item = WorkItem(
        id="OUT-264",
        title="Call Leon",
        status="todo",
        priority="high",
        due_date="2026-02-14",
        tags=["phone", "urgent"],
        tag_categories={"context": ["phone"], "priority": ["urgent"]},
        eisenhower_quadrant="q1",
        eisenhower_urgent=True,
        eisenhower_important=True,
        source="reminder",
        reminder_id="x-apple-reminder://ABC123",
        description="Discuss equity partner timeline",
        created=datetime.now(),
        updated=datetime.now()
    )

    file_path = adapter.create(work_item)

    assert file_path.exists()
    assert file_path.name.startswith("OUT-264")
    assert file_path.suffix == ".md"

    # Verify content
    content = file_path.read_text()
    assert "id: OUT-264" in content
    assert "title: Call Leon" in content
    assert "# Call Leon" in content
    assert "Discuss equity partner timeline" in content

def test_read_work_item_file(temp_work_dir):
    """Should read work item from file and parse frontmatter"""
    # Create test file
    file_path = temp_work_dir / "OUT-264-call-leon.md"
    file_path.write_text("""---
id: OUT-264
title: Call Leon
status: todo
priority: high
due_date: "2026-02-14"
tags:
  - phone
  - urgent
eisenhower_quadrant: q1
eisenhower_urgent: true
eisenhower_important: true
source: reminder
reminder_id: "x-apple-reminder://ABC123"
---

# Call Leon

## Description
Discuss equity partner timeline

## Steps
- [ ] Call Leon
- [ ] Discuss timeline
""")

    adapter = WorkItemFileAdapter(work_dir=temp_work_dir)
    work_item = adapter.read("OUT-264")

    assert work_item.id == "OUT-264"
    assert work_item.title == "Call Leon"
    assert "phone" in work_item.tags
    assert work_item.eisenhower_quadrant == "q1"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_workitems.py::test_create_work_item_file -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement WorkItemFileAdapter**

```python
# .claude/reminders/adapters/workitems.py
import re
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional
from reminders.core.models import WorkItem

class WorkItemFileAdapter:
    """Read/write work items as markdown files with YAML frontmatter"""

    def __init__(self, work_dir: Path = None):
        if work_dir is None:
            work_dir = Path("/Users/touttram/CODE/AAGLOBAL/.claude/work/tasks")
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def create(self, work_item: WorkItem) -> Path:
        """Create work item markdown file"""
        # Generate filename
        filename = self._generate_filename(work_item)
        file_path = self.work_dir / filename

        # Generate content
        content = self._generate_content(work_item)

        # Write file
        file_path.write_text(content)

        return file_path

    def read(self, work_item_id: str) -> Optional[WorkItem]:
        """Read work item from file"""
        # Find file by ID
        file_path = self._find_file(work_item_id)
        if not file_path:
            return None

        # Parse frontmatter and content
        content = file_path.read_text()
        frontmatter, body = self._parse_frontmatter(content)

        # Extract description
        description = self._extract_description(body)

        # Build WorkItem
        return WorkItem(
            id=frontmatter.get("id", ""),
            title=frontmatter.get("title", ""),
            status=frontmatter.get("status", "todo"),
            priority=frontmatter.get("priority", "low"),
            due_date=frontmatter.get("due_date"),
            tags=frontmatter.get("tags", []),
            tag_categories=frontmatter.get("tag_categories", {}),
            eisenhower_quadrant=frontmatter.get("eisenhower_quadrant", "q4"),
            eisenhower_urgent=frontmatter.get("eisenhower_urgent", False),
            eisenhower_important=frontmatter.get("eisenhower_important", False),
            source=frontmatter.get("source", "manual"),
            reminder_id=frontmatter.get("reminder_id"),
            reminder_list=frontmatter.get("reminder_list"),
            branch=frontmatter.get("branch"),
            description=description,
            created=self._parse_datetime(frontmatter.get("created")),
            updated=self._parse_datetime(frontmatter.get("updated"))
        )

    def update(self, work_item: WorkItem):
        """Update existing work item file"""
        file_path = self._find_file(work_item.id)
        if not file_path:
            raise FileNotFoundError(f"Work item {work_item.id} not found")

        # Update timestamp
        work_item.updated = datetime.now()

        # Regenerate content
        content = self._generate_content(work_item)
        file_path.write_text(content)

    def delete(self, work_item_id: str):
        """Delete work item file"""
        file_path = self._find_file(work_item_id)
        if file_path:
            file_path.unlink()

    def list_all(self) -> list[WorkItem]:
        """List all work items"""
        work_items = []
        for file_path in self.work_dir.glob("OUT-*.md"):
            work_item = self.read(self._extract_id_from_filename(file_path.name))
            if work_item:
                work_items.append(work_item)
        return work_items

    def _generate_filename(self, work_item: WorkItem) -> str:
        """Generate filename from work item"""
        # Clean title for filename
        clean_title = work_item.title.lower()[:50]
        clean_title = re.sub(r'[^\w\s-]', '', clean_title)
        clean_title = re.sub(r'[\s_]+', '-', clean_title)
        clean_title = re.sub(r'-+', '-', clean_title).strip('-')

        return f"{work_item.id}-{clean_title}.md"

    def _generate_content(self, work_item: WorkItem) -> str:
        """Generate markdown content with YAML frontmatter"""
        # Build frontmatter
        frontmatter = {
            "id": work_item.id,
            "title": work_item.title,
            "type": "task",
            "status": work_item.status,
            "priority": work_item.priority,
            "created": work_item.created.isoformat() if work_item.created else datetime.now().isoformat(),
            "updated": work_item.updated.isoformat() if work_item.updated else datetime.now().isoformat(),
            "branch": work_item.branch,
            "source": work_item.source,
            "eisenhower_quadrant": work_item.eisenhower_quadrant,
            "eisenhower_urgent": work_item.eisenhower_urgent,
            "eisenhower_important": work_item.eisenhower_important,
        }

        if work_item.due_date:
            frontmatter["due_date"] = work_item.due_date

        if work_item.tags:
            frontmatter["tags"] = work_item.tags

        if work_item.tag_categories:
            frontmatter["tag_categories"] = work_item.tag_categories

        if work_item.reminder_id:
            frontmatter["reminder_id"] = work_item.reminder_id

        if work_item.reminder_list:
            frontmatter["reminder_list"] = work_item.reminder_list

        # Build content
        content = "---\n"
        content += yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        content += "---\n\n"
        content += f"# {work_item.title}\n\n"
        content += "## Description\n"
        content += work_item.description or "No description provided"
        content += "\n\n"
        content += "## Steps\n"
        if work_item.steps:
            for step in work_item.steps:
                content += f"- [ ] {step}\n"
        else:
            content += "- [ ] Review task details\n"
            content += "- [ ] Complete task\n"
            content += "- [ ] Mark as done\n"

        return content

    def _find_file(self, work_item_id: str) -> Optional[Path]:
        """Find work item file by ID"""
        files = list(self.work_dir.glob(f"{work_item_id}-*.md"))
        return files[0] if files else None

    def _extract_id_from_filename(self, filename: str) -> str:
        """Extract OUT-XXX from filename"""
        match = re.match(r'(OUT-\d+)', filename)
        return match.group(1) if match else ""

    def _parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """Parse YAML frontmatter from markdown"""
        match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
        if not match:
            return {}, content

        frontmatter_text = match.group(1)
        body = match.group(2)

        frontmatter = yaml.safe_load(frontmatter_text)
        return frontmatter, body

    def _extract_description(self, body: str) -> str:
        """Extract description from markdown body"""
        match = re.search(r'## Description\n(.*?)(?:\n##|$)', body, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str)
        except:
            return None
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_workitems.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add .claude/reminders/adapters/workitems.py .claude/reminders/tests/unit/test_workitems.py
git commit -m "feat(reminders): add work item file I/O adapter

- Add WorkItemFileAdapter for reading/writing markdown files
- Parse YAML frontmatter from work items
- Generate clean filenames from work item ID and title
- Support create, read, update, delete, list operations
- Add comprehensive unit tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: RemindersManager Core API

**Files:**
- Create: `.claude/reminders/core/manager.py`
- Create: `.claude/reminders/tests/unit/test_manager.py`

**Step 1: Write failing test for create_reminder**

```python
# .claude/reminders/tests/unit/test_manager.py
import pytest
from datetime import datetime
from reminders.core.manager import RemindersManager
from reminders.core.events import EventBus, WorkItemCreated
from reminders.tests.fixtures.mock_applescript import MockAppleScriptAdapter
from pathlib import Path

@pytest.fixture
def temp_work_dir(tmp_path):
    work_dir = tmp_path / "work" / "tasks"
    work_dir.mkdir(parents=True)
    return work_dir

@pytest.fixture
def manager(temp_work_dir):
    """Create RemindersManager with mock dependencies"""
    bus = EventBus()
    applescript = MockAppleScriptAdapter()
    return RemindersManager(
        event_bus=bus,
        applescript_adapter=applescript,
        work_dir=temp_work_dir
    )

def test_create_reminder_creates_work_item_and_pushes(manager, temp_work_dir):
    """Should create work item file and push to Reminders.app"""
    work_item = manager.create_reminder(
        title="Call Leon",
        due_date="2026-02-14",
        tags=["phone", "urgent"],
        priority="high"
    )

    # Check work item created
    assert work_item.id.startswith("OUT-")
    assert work_item.title == "Call Leon"
    assert "phone" in work_item.tags

    # Check file created
    files = list(temp_work_dir.glob("OUT-*.md"))
    assert len(files) == 1

    # Check pushed to Reminders.app (mock)
    assert len(manager.applescript.call_log) == 1
    assert manager.applescript.call_log[0][0] == "create"

def test_create_reminder_emits_event(manager):
    """Should emit WorkItemCreated event"""
    events = []
    manager.event_bus.subscribe(WorkItemCreated, lambda e: events.append(e))

    work_item = manager.create_reminder("Test task")

    assert len(events) == 1
    assert events[0].work_item_id == work_item.id
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_manager.py::test_create_reminder_creates_work_item_and_pushes -v
```

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement RemindersManager**

```python
# .claude/reminders/core/manager.py
from pathlib import Path
from datetime import datetime
from typing import Optional
from reminders.core.events import EventBus, WorkItemCreated, WorkItemUpdated, WorkItemCompleted, WorkItemDeleted
from reminders.core.models import WorkItem
from reminders.adapters.applescript import AppleScriptAdapter
from reminders.adapters.workitems import WorkItemFileAdapter

class RemindersManager:
    """Main API for managing reminders - everything goes through this"""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        applescript_adapter: Optional[AppleScriptAdapter] = None,
        work_dir: Optional[Path] = None
    ):
        self.event_bus = event_bus or EventBus()
        self.applescript = applescript_adapter or AppleScriptAdapter()
        self.workitems = WorkItemFileAdapter(work_dir=work_dir)
        self._next_id = self._get_next_work_item_id()

    def create_reminder(
        self,
        title: str,
        due_date: Optional[str] = None,
        tags: Optional[list[str]] = None,
        priority: str = "low",
        description: str = "",
        list_name: str = "Reminders"
    ) -> WorkItem:
        """Create a new reminder (work item + Reminders.app sync)"""
        # Generate work item ID
        work_item_id = f"OUT-{self._next_id}"
        self._next_id += 1

        # Classify into Eisenhower quadrant (simple heuristic for now)
        urgent = due_date is not None and priority in ["high", "urgent"]
        important = priority in ["high", "medium"] or bool(description)

        if urgent and important:
            quadrant = "q1"
        elif not urgent and important:
            quadrant = "q2"
        elif urgent and not important:
            quadrant = "q3"
        else:
            quadrant = "q4"

        # Create work item
        now = datetime.now()
        work_item = WorkItem(
            id=work_item_id,
            title=title,
            status="todo",
            priority=priority,
            due_date=due_date,
            tags=tags or [],
            eisenhower_quadrant=quadrant,
            eisenhower_urgent=urgent,
            eisenhower_important=important,
            source="manual",
            description=description,
            created=now,
            updated=now
        )

        # Save work item file
        self.workitems.create(work_item)

        # Push to Reminders.app
        reminder_id = self.applescript.create_reminder(
            name=title,
            body=self._build_reminder_body(work_item),
            tags=tags,
            due_date=due_date,
            priority=self._map_priority_to_apple(priority),
            list_name=list_name
        )

        # Update work item with reminder_id
        work_item.reminder_id = reminder_id
        work_item.reminder_list = list_name
        self.workitems.update(work_item)

        # Emit event
        self.event_bus.publish(WorkItemCreated(
            work_item_id=work_item_id,
            reminder_id=reminder_id
        ))

        return work_item

    def complete_reminder(self, work_item_id: str):
        """Mark reminder as completed"""
        work_item = self.workitems.read(work_item_id)
        if not work_item:
            raise ValueError(f"Work item {work_item_id} not found")

        # Update work item
        work_item.status = "done"
        work_item.updated = datetime.now()
        self.workitems.update(work_item)

        # Update in Reminders.app
        if work_item.reminder_id:
            self.applescript.update_reminder(
                work_item.reminder_id,
                completed=True
            )

        # Emit event
        self.event_bus.publish(WorkItemCompleted(work_item_id=work_item_id))

    def delete_reminder(self, work_item_id: str):
        """Delete reminder from both systems"""
        work_item = self.workitems.read(work_item_id)
        if not work_item:
            raise ValueError(f"Work item {work_item_id} not found")

        # Delete from Reminders.app
        if work_item.reminder_id:
            self.applescript.delete_reminder(work_item.reminder_id)

        # Delete work item file
        self.workitems.delete(work_item_id)

        # Emit event
        self.event_bus.publish(WorkItemDeleted(work_item_id=work_item_id))

    def list_reminders(
        self,
        tags: Optional[list[str]] = None,
        quadrant: Optional[str] = None,
        status: str = "todo"
    ) -> list[WorkItem]:
        """List reminders with optional filters"""
        all_items = self.workitems.list_all()

        # Filter by status
        items = [item for item in all_items if item.status == status]

        # Filter by tags
        if tags:
            items = [
                item for item in items
                if any(tag in item.tags for tag in tags)
            ]

        # Filter by quadrant
        if quadrant:
            items = [item for item in items if item.eisenhower_quadrant == quadrant]

        return items

    def get_reminder(self, work_item_id: str) -> Optional[WorkItem]:
        """Get single reminder by ID"""
        return self.workitems.read(work_item_id)

    def _get_next_work_item_id(self) -> int:
        """Find highest OUT-2XX ID and increment"""
        all_items = self.workitems.list_all()
        if not all_items:
            return 220

        highest = 220
        for item in all_items:
            if item.id.startswith("OUT-"):
                try:
                    num = int(item.id.split("-")[1])
                    if 200 <= num < 300:
                        highest = max(highest, num)
                except:
                    pass

        return highest + 1

    def _build_reminder_body(self, work_item: WorkItem) -> str:
        """Build reminder body with embedded metadata"""
        body = f"---\n{work_item.id}\n"
        body += f"eisenhower_quadrant: {work_item.eisenhower_quadrant}\n"
        body += f"branch: {work_item.branch}\n"
        body += "---\n"
        body += work_item.description
        return body

    def _map_priority_to_apple(self, priority: str) -> int:
        """Map priority string to Apple priority int"""
        mapping = {
            "high": 1,
            "urgent": 1,
            "medium": 5,
            "low": 9,
            "none": 0
        }
        return mapping.get(priority.lower(), 0)
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_manager.py -v
```

Expected: All PASS

**Step 5: Add more tests**

```python
# Append to test_manager.py

def test_complete_reminder(manager):
    """Should mark work item and reminder as completed"""
    work_item = manager.create_reminder("Test task")

    manager.complete_reminder(work_item.id)

    # Check work item updated
    updated_item = manager.get_reminder(work_item.id)
    assert updated_item.status == "done"

    # Check Reminders.app updated
    reminder = manager.applescript.get_reminder(work_item.reminder_id)
    assert reminder["completed"] is True

def test_delete_reminder(manager, temp_work_dir):
    """Should delete from both systems"""
    work_item = manager.create_reminder("Test task")

    manager.delete_reminder(work_item.id)

    # Check work item deleted
    assert manager.get_reminder(work_item.id) is None

    # Check file deleted
    files = list(temp_work_dir.glob("OUT-*.md"))
    assert len(files) == 0

def test_list_reminders_with_filters(manager):
    """Should filter reminders by tags and quadrant"""
    manager.create_reminder("Task 1", tags=["aussuper"], priority="high")
    manager.create_reminder("Task 2", tags=["phone"], priority="low")
    manager.create_reminder("Task 3", tags=["aussuper", "phone"], priority="high")

    # Filter by tag
    aussuper_items = manager.list_reminders(tags=["aussuper"])
    assert len(aussuper_items) == 2

    # Filter by quadrant
    q1_items = manager.list_reminders(quadrant="q1")
    assert all(item.eisenhower_quadrant == "q1" for item in q1_items)
```

**Step 6: Run all manager tests**

```bash
pytest tests/unit/test_manager.py -v
```

Expected: All PASS

**Step 7: Commit**

```bash
git add .claude/reminders/core/manager.py .claude/reminders/tests/unit/test_manager.py
git commit -m "feat(reminders): add RemindersManager core API

- Add create_reminder with work item + Reminders.app sync
- Add complete_reminder, delete_reminder
- Add list_reminders with tag/quadrant filters
- Add get_reminder for single item lookup
- Auto-generate work item IDs (OUT-2XX)
- Classify into Eisenhower quadrants
- Emit events for all operations
- Add comprehensive unit tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: CLI Plugin

**Files:**
- Create: `.claude/reminders/plugins/cli.py`
- Create: `.claude/reminders/tests/integration/test_cli.py`

**Step 1: Install Click**

```bash
cd .claude/reminders
pip install click
```

**Step 2: Write CLI implementation**

```python
# .claude/reminders/plugins/cli.py
import click
from pathlib import Path
from reminders.core.manager import RemindersManager

@click.group()
@click.pass_context
def main(ctx):
    """Reminders Manager - Bi-directional sync with macOS Reminders"""
    ctx.ensure_object(dict)
    ctx.obj['manager'] = RemindersManager()

@main.command()
@click.argument('title')
@click.option('--due', help='Due date (YYYY-MM-DD or natural language)')
@click.option('--priority', default='low', type=click.Choice(['low', 'medium', 'high', 'urgent']))
@click.option('--tag', 'tags', multiple=True, help='Add tag (can be used multiple times)')
@click.option('--list', 'list_name', default='Reminders', help='Reminders list name')
@click.option('--notes', default='', help='Description/notes')
@click.pass_context
def add(ctx, title, due, priority, tags, list_name, notes):
    """Create a new reminder"""
    manager = ctx.obj['manager']

    work_item = manager.create_reminder(
        title=title,
        due_date=due,
        tags=list(tags),
        priority=priority,
        description=notes,
        list_name=list_name
    )

    click.echo(f"✅ Created {work_item.id}: {work_item.title}")
    if work_item.reminder_id:
        click.echo(f"📱 Synced to Reminders.app")

@main.command()
@click.option('--tag', 'tags', multiple=True, help='Filter by tag')
@click.option('--q1', 'quadrant', flag_value='q1', help='Show Q1 (urgent & important)')
@click.option('--q2', 'quadrant', flag_value='q2', help='Show Q2 (not urgent but important)')
@click.option('--q3', 'quadrant', flag_value='q3', help='Show Q3 (urgent but not important)')
@click.option('--q4', 'quadrant', flag_value='q4', help='Show Q4 (not urgent & not important)')
@click.option('--status', default='todo', help='Filter by status')
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'compact', 'json']))
@click.pass_context
def list(ctx, tags, quadrant, status, output_format):
    """List reminders with filters"""
    manager = ctx.obj['manager']

    items = manager.list_reminders(
        tags=list(tags) if tags else None,
        quadrant=quadrant,
        status=status
    )

    if not items:
        click.echo("No reminders found")
        return

    if output_format == 'compact':
        for item in items:
            click.echo(f"{item.id}  {item.title}")

    elif output_format == 'json':
        import json
        data = [
            {
                "id": item.id,
                "title": item.title,
                "status": item.status,
                "priority": item.priority,
                "due_date": item.due_date,
                "tags": item.tags,
                "quadrant": item.eisenhower_quadrant
            }
            for item in items
        ]
        click.echo(json.dumps(data, indent=2))

    else:  # table
        # Simple table format
        click.echo("─" * 80)
        click.echo(f"{'ID':<10} {'Title':<40} {'Due':<12} {'Tags':<18}")
        click.echo("─" * 80)
        for item in items:
            tags_str = ", ".join(item.tags[:3])
            if len(item.tags) > 3:
                tags_str += "..."
            click.echo(f"{item.id:<10} {item.title[:38]:<40} {item.due_date or 'None':<12} {tags_str:<18}")
        click.echo("─" * 80)
        click.echo(f"{len(items)} reminders found")

@main.command()
@click.argument('work_item_id')
@click.pass_context
def complete(ctx, work_item_id):
    """Mark reminder as completed"""
    manager = ctx.obj['manager']

    manager.complete_reminder(work_item_id)
    click.echo(f"✅ Completed {work_item_id}")

@main.command()
@click.argument('work_item_id')
@click.confirmation_option(prompt='Are you sure you want to delete this reminder?')
@click.pass_context
def delete(ctx, work_item_id):
    """Delete a reminder"""
    manager = ctx.obj['manager']

    manager.delete_reminder(work_item_id)
    click.echo(f"🗑️  Deleted {work_item_id}")

@main.command()
@click.argument('work_item_id')
@click.pass_context
def show(ctx, work_item_id):
    """Show detailed reminder info"""
    manager = ctx.obj['manager']

    item = manager.get_reminder(work_item_id)
    if not item:
        click.echo(f"❌ Work item {work_item_id} not found")
        return

    click.echo(f"\n{'='*60}")
    click.echo(f"ID: {item.id}")
    click.echo(f"Title: {item.title}")
    click.echo(f"Status: {item.status}")
    click.echo(f"Priority: {item.priority}")
    click.echo(f"Due: {item.due_date or 'None'}")
    click.echo(f"Tags: {', '.join(item.tags) if item.tags else 'None'}")
    click.echo(f"Quadrant: {item.eisenhower_quadrant}")
    click.echo(f"Source: {item.source}")
    if item.reminder_id:
        click.echo(f"Reminder ID: {item.reminder_id}")
    click.echo(f"\nDescription:")
    click.echo(item.description or "No description")
    click.echo(f"{'='*60}\n")

if __name__ == '__main__':
    main()
```

**Step 3: Test CLI manually**

```bash
cd .claude/reminders

# Add reminder
reminder add "Test CLI" --due 2026-02-20 --tag test --priority high

# List reminders
reminder list

# Show reminder
reminder show OUT-XXX  # Use actual ID from add output

# Complete reminder
reminder complete OUT-XXX

# Delete reminder
reminder delete OUT-XXX
```

Expected: All commands work correctly

**Step 4: Write integration test**

```python
# .claude/reminders/tests/integration/test_cli.py
import subprocess
import pytest
from pathlib import Path

@pytest.fixture
def temp_work_dir(tmp_path):
    work_dir = tmp_path / "work" / "tasks"
    work_dir.mkdir(parents=True)
    return work_dir

def test_cli_add_command(temp_work_dir, monkeypatch):
    """Test reminder add command"""
    # Set work dir for test
    monkeypatch.setenv("REMINDERS_WORK_DIR", str(temp_work_dir))

    result = subprocess.run(
        ["reminder", "add", "Test task", "--due", "2026-02-20", "--tag", "test"],
        capture_output=True,
        text=True,
        env={"REMINDERS_WORK_DIR": str(temp_work_dir)}
    )

    assert result.returncode == 0
    assert "Created OUT-" in result.stdout

    # Verify file created
    files = list(temp_work_dir.glob("OUT-*.md"))
    assert len(files) == 1

def test_cli_list_command(temp_work_dir, monkeypatch):
    """Test reminder list command"""
    monkeypatch.setenv("REMINDERS_WORK_DIR", str(temp_work_dir))

    # Add a task first
    subprocess.run(
        ["reminder", "add", "Test task"],
        env={"REMINDERS_WORK_DIR": str(temp_work_dir)}
    )

    # List tasks
    result = subprocess.run(
        ["reminder", "list"],
        capture_output=True,
        text=True,
        env={"REMINDERS_WORK_DIR": str(temp_work_dir)}
    )

    assert result.returncode == 0
    assert "Test task" in result.stdout
```

**Step 5: Run integration tests**

```bash
pytest tests/integration/test_cli.py -v
```

Expected: PASS (may need to adjust based on actual CLI behavior)

**Step 6: Commit**

```bash
git add .claude/reminders/plugins/cli.py .claude/reminders/tests/integration/test_cli.py
git commit -m "feat(reminders): add CLI plugin with click

- Add reminder command group (add, list, complete, delete, show)
- Support filters (tags, quadrant, status)
- Multiple output formats (table, compact, json)
- Confirmation prompts for destructive operations
- Add integration tests for CLI commands

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Documentation & Final Testing

**Files:**
- Create: `.claude/reminders/docs/USAGE.md`
- Update: `.claude/reminders/README.md`
- Run full test suite

**Step 1: Create usage documentation**

```markdown
# .claude/reminders/docs/USAGE.md

# Reminders Manager - Usage Guide

## Installation

```bash
cd .claude/reminders
pip install -e ".[dev]"
```

## Quick Start

### Create a Reminder

```bash
# Basic reminder
reminder add "Call Leon"

# With due date and tags
reminder add "Equity partner form" --due 2026-02-20 --tag equity-partner --tag admin --priority high

# With notes
reminder add "Review docs" --notes "Review the architecture documentation"
```

### List Reminders

```bash
# List all
reminder list

# Filter by tag
reminder list --tag aussuper

# Show only Q1 (urgent & important)
reminder list --q1

# Compact format
reminder list --format compact

# JSON format (for scripts)
reminder list --format json
```

### Complete a Reminder

```bash
reminder complete OUT-264
```

### Delete a Reminder

```bash
reminder delete OUT-264
```

### Show Reminder Details

```bash
reminder show OUT-264
```

## Python API

```python
from reminders.core.manager import RemindersManager

# Create manager
rm = RemindersManager()

# Create reminder
work_item = rm.create_reminder(
    title="Call Leon",
    due_date="2026-02-14",
    tags=["phone", "urgent"],
    priority="high"
)

# List reminders
items = rm.list_reminders(tags=["aussuper"])

# Complete reminder
rm.complete_reminder("OUT-264")

# Delete reminder
rm.delete_reminder("OUT-264")
```

## Event Subscription

```python
from reminders.core.events import WorkItemCreated

def on_work_item_created(event):
    print(f"New work item: {event.work_item_id}")

rm.event_bus.subscribe(WorkItemCreated, on_work_item_created)
```

## Testing

```bash
# Run all tests
pytest tests/ -v --cov

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Coverage report
pytest --cov=reminders --cov-report=html
```

## Troubleshooting

### Reminders.app Permission Denied

1. Open System Preferences → Security & Privacy → Automation
2. Grant Terminal/Claude Code access to Reminders

### Work Item Not Found

Check the work directory:
```bash
ls -la /Users/touttram/CODE/AAGLOBAL/.claude/work/tasks/
```
```

**Step 2: Update main README**

Add to `.claude/reminders/README.md`:

```markdown
## Phase 1 Complete ✅

Core foundation (v0.1) is now complete:
- ✅ Data models (WorkItem, Reminder, Events)
- ✅ Event bus (pub/sub system)
- ✅ AppleScript adapter (read/write Reminders.app)
- ✅ Work item file I/O (YAML frontmatter + markdown)
- ✅ RemindersManager API
- ✅ CLI (add, list, complete, delete, show)
- ✅ Unit tests (80%+ coverage)

## Next: Phase 2 - Sync Engine

- [ ] Bi-directional sync (push/pull)
- [ ] Conflict detection
- [ ] Manual conflict resolution
- [ ] Sync state tracking
```

**Step 3: Run full test suite**

```bash
cd .claude/reminders

# Run all tests with coverage
pytest tests/ -v --cov=reminders --cov-report=term --cov-report=html

# Check coverage is >80%
```

Expected: All tests PASS, coverage >80%

**Step 4: Final commit**

```bash
git add .claude/reminders/docs/USAGE.md .claude/reminders/README.md
git commit -m "docs(reminders): add usage guide and update README

- Add comprehensive usage documentation
- Include CLI examples
- Include Python API examples
- Add troubleshooting section
- Mark Phase 1 as complete in README

Phase 1 (v0.1) Complete:
- Core foundation implemented
- 80%+ test coverage
- Ready for Phase 2 (Sync Engine)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Completion Checklist

### Phase 1 (v0.1) - Core Foundation

- [x] Project scaffold and dependencies
- [x] Data models (WorkItem, Reminder)
- [x] Event system (Event bus, event types)
- [x] AppleScript adapter (Reminders.app interface)
- [x] Work item file I/O (YAML + markdown)
- [x] RemindersManager API (create, list, complete, delete)
- [x] CLI plugin (add, list, complete, delete, show)
- [x] Unit tests (80%+ coverage)
- [x] Integration tests (CLI)
- [x] Documentation (README, USAGE)

**Estimated Time:** 8-12 hours
**Test Coverage Target:** 80%+
**Files Created:** ~20 files

---

## Plan Complete

Plan saved to `docs/plans/2026-02-13-reminders-tool-implementation.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
