#!/usr/bin/env python3
"""Import reminders from AppleScript output into file-native task system"""

import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Add scripts dir to path so we can import task_registry
sys.path.insert(0, str(Path(__file__).resolve().parent))
# Add .claude dir to path so we can import reminders packages
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from task_registry import TaskRegistry
TODAY = datetime.now().date()
URGENT_THRESHOLD_DAYS = 3

# Priority mapping
PRIORITY_MAP = {
    0: "low",
    1: "high",
    5: "medium",
    9: "low"
}


def fetch_reminders_from_applescript():
    """Fetch reminders from macOS Reminders app using AppleScript"""
    applescript = '''
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
                set output to output & listName & "|" & rId & "|" & rName & "|" & rBody & "|" & rDueDate & "|" & rPriority & linefeed
            end if
        end repeat
    end repeat
    return output
end tell
'''

    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            timeout=120  # Increased for large reminder lists
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"❌ AppleScript error: {result.stderr}")
            return ""
    except subprocess.TimeoutExpired:
        print("❌ AppleScript timed out")
        return ""
    except Exception as e:
        print(f"❌ Error running AppleScript: {e}")
        return ""


def parse_due_date(date_str):
    """Parse AppleScript date string to YYYY-MM-DD"""
    if date_str == "missing value" or not date_str or date_str == "":
        return None

    # Parse "Thursday, 12 February 2026 at 12:00:00 am"
    try:
        parts = date_str.split(" at ")[0]  # Remove time portion
        date_obj = datetime.strptime(parts, "%A, %d %B %Y")
        return date_obj.date()
    except:
        return None


def classify_reminder(priority, due_date, has_body):
    """Classify reminder into Eisenhower quadrant"""
    # Determine urgent
    urgent = False
    if due_date:
        days_until_due = (due_date - TODAY).days
        if days_until_due <= URGENT_THRESHOLD_DAYS:
            urgent = True
    if priority == 1:  # P1 is always urgent
        urgent = True

    # Determine important
    important = False
    if priority in [1, 5]:  # P1 or P5
        important = True
    if has_body:
        important = True
    if due_date:
        important = True

    # Assign quadrant
    if urgent and important:
        return "q1", urgent, important
    elif not urgent and important:
        return "q2", urgent, important
    elif urgent and not important:
        return "q3", urgent, important
    else:
        return "q4", urgent, important


def parse_reminder(line):
    """Parse a pipe-delimited reminder line into structured data.

    Returns a dict with all fields needed by TaskRegistry.create_task(),
    or None if the line is malformed.
    """
    parts = line.split('|')
    if len(parts) != 6:
        print(f"⚠️  Skipping malformed reminder: {line[:50]}...")
        return None

    list_name, reminder_id, name, body, due_date_str, priority_str = parts

    priority_num = int(priority_str)
    priority = PRIORITY_MAP.get(priority_num, "low")
    due_date = parse_due_date(due_date_str)
    due_date_formatted = due_date.isoformat() if due_date else None
    has_body = body != "missing value" and body != "" and body
    description = body if has_body else "No description provided"

    # Classify into Eisenhower quadrant
    quadrant, is_urgent, is_important = classify_reminder(priority_num, due_date, has_body)

    # Strip [OUT-XXX] prefix from round-tripped titles
    name = re.sub(r'^\[OUT-\d+\]\s*', '', name)

    return {
        "title": name,
        "source": "reminder",
        "reminder_id": reminder_id,
        "description": description,
        "priority": priority,
        "due_date": due_date_formatted,
        "list_name": list_name,
        "eisenhower_quadrant": quadrant,
        "eisenhower_urgent": is_urgent,
        "eisenhower_important": is_important,
    }


# Main execution
print("🔄 Fetching reminders from macOS Reminders app...")
print()

reminders_data = fetch_reminders_from_applescript()

if not reminders_data:
    print("❌ No reminders found or error fetching reminders")
    print()
    print("Troubleshooting:")
    print("1. Check System Preferences → Security & Privacy → Automation")
    print("2. Ensure Terminal/Claude Code has access to Reminders")
    print("3. Try opening Reminders app manually")
    exit(1)

print("📊 Processing reminders...")
print()

registry = TaskRegistry()
quadrant_counts = {"q1": 0, "q2": 0, "q3": 0, "q4": 0}
created_tasks = []
skipped = 0

for line in reminders_data.strip().split('\n'):
    if not line:
        continue

    data = parse_reminder(line)
    if data is None:
        skipped += 1
        continue

    out_id = registry.create_task(**data)

    if out_id is None:
        print(f"⏭️  Skipping duplicate: {data['title']}")
        skipped += 1
        continue

    quadrant_counts[data["eisenhower_quadrant"]] += 1
    created_tasks.append(out_id)

# Print summary
print("✅ Reminders Import Complete")
print()
print(f"Imported: {len(created_tasks)} tasks")
print(f"- Q1 (Do First): {quadrant_counts['q1']} tasks")
print(f"- Q2 (Schedule): {quadrant_counts['q2']} tasks")
print(f"- Q3 (Delegate): {quadrant_counts['q3']} tasks")
print(f"- Q4 (Eliminate): {quadrant_counts['q4']} tasks")
print()

if skipped > 0:
    print(f"Skipped: {skipped} tasks (already imported)")
    print()

if created_tasks:
    print("Files created:")
    for task in created_tasks[:10]:  # Show first 10
        print(f"  - {task}")
    if len(created_tasks) > 10:
        print(f"  ... and {len(created_tasks) - 10} more")
