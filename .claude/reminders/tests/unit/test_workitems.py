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


def test_update_work_item(temp_work_dir):
    """Should update existing work item file"""
    adapter = WorkItemFileAdapter(work_dir=temp_work_dir)

    work_item = WorkItem(
        id="OUT-265",
        title="Review docs",
        status="todo",
        priority="medium",
        created=datetime.now(),
        updated=datetime.now()
    )

    adapter.create(work_item)

    # Update status
    work_item.status = "in-progress"
    adapter.update(work_item)

    # Re-read and verify
    updated = adapter.read("OUT-265")
    assert updated.status == "in-progress"


def test_delete_work_item(temp_work_dir):
    """Should delete work item file"""
    adapter = WorkItemFileAdapter(work_dir=temp_work_dir)

    work_item = WorkItem(
        id="OUT-266",
        title="Delete me",
        created=datetime.now(),
        updated=datetime.now()
    )

    adapter.create(work_item)
    adapter.delete("OUT-266")

    assert adapter.read("OUT-266") is None
    assert len(list(temp_work_dir.glob("OUT-266-*.md"))) == 0


def test_list_all_work_items(temp_work_dir):
    """Should list all work items in directory"""
    adapter = WorkItemFileAdapter(work_dir=temp_work_dir)

    for i in range(3):
        work_item = WorkItem(
            id=f"OUT-{270 + i}",
            title=f"Task {i}",
            created=datetime.now(),
            updated=datetime.now()
        )
        adapter.create(work_item)

    items = adapter.list_all()
    assert len(items) == 3


def test_read_nonexistent_returns_none(temp_work_dir):
    """Should return None for nonexistent work item"""
    adapter = WorkItemFileAdapter(work_dir=temp_work_dir)
    assert adapter.read("OUT-999") is None
