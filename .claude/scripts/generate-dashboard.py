#!/usr/bin/env python3
"""Generate Eisenhower Matrix dashboard from task files"""

import os
import re
import sys
import json
from datetime import datetime
from pathlib import Path

# Add .claude dir to path so we can import reminders.core.paths
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from reminders.core.paths import WORK_DIR, TEMPLATE_DIR, DASHBOARD_DIR

# Paths
TEMPLATE_PATH = TEMPLATE_DIR / "eisenhower-template.html"

def extract_frontmatter(file_path):
    """Extract YAML frontmatter from markdown file"""
    with open(file_path, 'r') as f:
        content = f.read()

    # Find frontmatter between --- markers
    match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL | re.MULTILINE)
    if not match:
        return None

    frontmatter_text = match.group(1)
    frontmatter = {}

    # Parse YAML fields
    for line in frontmatter_text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            frontmatter[key] = value

    # Extract description from markdown
    description_match = re.search(r'## Description\n(.+?)(?:\n##|$)', content, re.DOTALL)
    if description_match:
        frontmatter['description'] = description_match.group(1).strip()
    else:
        frontmatter['description'] = ""

    return frontmatter


def scan_work_items():
    """Scan all work items. Uses registry if available, falls back to file scan."""
    registry_path = WORK_DIR / "task-registry.yml"

    if registry_path.exists():
        return _scan_from_registry(registry_path)
    else:
        return _scan_from_files()


def _build_task(file_path, frontmatter):
    """Build a task dict from frontmatter. Returns (quadrant, task) or None."""
    quadrant = frontmatter.get('eisenhower_quadrant', '')
    if not quadrant or quadrant not in ['q1', 'q2', 'q3', 'q4']:
        print(f"⚠️  Skipping {file_path.name} - no valid quadrant")
        return None

    task = {
        "id": frontmatter.get('id', ''),
        "title": frontmatter.get('title', ''),
        "status": frontmatter.get('status', ''),
        "priority": frontmatter.get('priority', ''),
        "due_date": frontmatter.get('due_date', ''),
        "source": frontmatter.get('source', 'manual'),
        "reminder_list": frontmatter.get('reminder_list', ''),
        "file_path": str(file_path.relative_to(WORK_DIR.parent)),
        "description": frontmatter.get('description', ''),
        "eisenhower_urgent": frontmatter.get('eisenhower_urgent', '') == 'true',
        "eisenhower_important": frontmatter.get('eisenhower_important', '') == 'true',
        "auto_classified": False
    }

    return quadrant, task


def _scan_from_registry(registry_path):
    """Read task list from registry, then load full details from files."""
    import yaml
    with open(registry_path) as f:
        registry = yaml.safe_load(f)

    tasks = {"q1": [], "q2": [], "q3": [], "q4": []}
    entries = registry.get("entries", {})
    task_dir = WORK_DIR / "tasks"
    bug_dir = WORK_DIR / "bugs"

    print(f"📂 Scanning {len(entries)} work items from registry...")

    for out_id, entry in entries.items():
        filename = entry.get("file", "")
        if not filename:
            continue

        # Look in tasks/ first, then bugs/
        file_path = task_dir / filename
        if not file_path.exists():
            file_path = bug_dir / filename
        if not file_path.exists():
            continue

        # Skip done items (check both registry status and done/ directory)
        reg_status = entry.get("status", "")
        if reg_status == "done" or '/done/' in str(file_path):
            continue

        frontmatter = extract_frontmatter(file_path)
        if not frontmatter:
            continue

        result = _build_task(file_path, frontmatter)
        if result:
            quadrant, task = result
            tasks[quadrant].append(task)

    return tasks


def _scan_from_files():
    """Original file-scan approach as fallback."""
    tasks = {"q1": [], "q2": [], "q3": [], "q4": []}

    # Scan tasks
    task_files = list((WORK_DIR / "tasks").glob("OUT-*.md"))

    # Scan bugs (if any)
    if (WORK_DIR / "bugs").exists():
        task_files.extend(list((WORK_DIR / "bugs").glob("OUT-*.md")))

    print(f"📂 Scanning {len(task_files)} work items (no registry)...")

    for file_path in task_files:
        # Skip done items
        if '/done/' in str(file_path):
            continue

        frontmatter = extract_frontmatter(file_path)
        if not frontmatter:
            continue

        result = _build_task(file_path, frontmatter)
        if result:
            quadrant, task = result
            tasks[quadrant].append(task)

    return tasks


def generate_dashboard(tasks):
    """Generate HTML dashboard from template"""
    # Load template
    with open(TEMPLATE_PATH, 'r') as f:
        template = f.read()

    # Calculate counts and metadata
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %I:%M %p")
    date = now.strftime("%b %d, %Y")

    q1_count = len(tasks['q1'])
    q2_count = len(tasks['q2'])
    q3_count = len(tasks['q3'])
    q4_count = len(tasks['q4'])
    total_tasks = q1_count + q2_count + q3_count + q4_count

    # Add metadata to tasks object
    dashboard_data = {
        "metadata": {
            "generated_at": now.isoformat(),
            "total_tasks": total_tasks,
            "q1_count": q1_count,
            "q2_count": q2_count,
            "q3_count": q3_count,
            "q4_count": q4_count
        },
        "q1": tasks['q1'],
        "q2": tasks['q2'],
        "q3": tasks['q3'],
        "q4": tasks['q4']
    }

    # Convert to JSON for injection
    json_data = json.dumps(dashboard_data, indent=2)

    # Replace placeholders in template
    html = template.replace('{timestamp}', timestamp)
    html = html.replace('{date}', date)
    html = html.replace('{total_tasks}', str(total_tasks))
    html = html.replace('{q1_count}', str(q1_count))
    html = html.replace('{q2_count}', str(q2_count))
    html = html.replace('{q3_count}', str(q3_count))
    html = html.replace('{q4_count}', str(q4_count))
    html = html.replace('{INJECTED_JSON_DATA}', json_data)

    # Generate filename
    filename = f"eisenhower-{now.strftime('%Y-%m-%d-%H%M')}.html"
    filepath = DASHBOARD_DIR / filename

    # Write file
    with open(filepath, 'w') as f:
        f.write(html)

    # Create symlink to latest
    latest_link = DASHBOARD_DIR / "eisenhower-latest.html"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(filename)

    return filepath, q1_count, q2_count, q3_count, q4_count


def update_gist(filepath):
    """Update the permanent gist for mobile access. Returns success bool."""
    import subprocess
    gist_id = "20f5befb1e2f8cef427b784e6860ddf8"
    result = subprocess.run(
        ["gh", "gist", "edit", gist_id, str(filepath), "--filename", "eisenhower-dashboard.html"],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


if __name__ == "__main__":
    import subprocess

    print("📊 Generating Eisenhower Matrix Dashboard")
    print()

    tasks = scan_work_items()
    filepath, q1, q2, q3, q4 = generate_dashboard(tasks)

    print()
    print("✅ Dashboard Generated")
    print()
    print(f"File: {filepath}")
    print(f"Latest: {filepath.parent}/eisenhower-latest.html")
    print()
    print("Tasks by Quadrant:")
    print(f"- 🔥 Q1 (Do First): {q1} tasks")
    print(f"- 📅 Q2 (Schedule): {q2} tasks")
    print(f"- 🔀 Q3 (Delegate): {q3} tasks")
    print(f"- 🗑️  Q4 (Eliminate): {q4} tasks")
    print()

    file_url = f"file://{filepath}"
    subprocess.run(["open", file_url])
    print(f"Opening in browser: {file_url}")

    print()
    print("📤 Updating mobile dashboard gist...")
    if update_gist(filepath):
        gist_id = "20f5befb1e2f8cef427b784e6860ddf8"
        print(f"✅ Mobile dashboard updated!")
        print(f"🔗 https://gist.githack.com/outtram/{gist_id}/raw/eisenhower-dashboard.html")
    else:
        print(f"⚠️  Failed to update gist")
