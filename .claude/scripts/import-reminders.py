#!/usr/bin/env python3
"""Import reminders from AppleScript output into file-native task system"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
TASK_DIR = Path("/Users/touttram/CODE/AAGLOBAL/.claude/work/tasks")
START_ID = 220
TODAY = datetime.now().date()
URGENT_THRESHOLD_DAYS = 3

# Priority mapping
PRIORITY_MAP = {
    0: "low",
    1: "high",
    5: "medium",
    9: "low"
}

# Reminder data (pipe-delimited from AppleScript)
reminders_data = """EISENHOWER_TEST|x-apple-reminder://0B00350D-D515-4F76-A4E3-9300FB89F0E4|Fix critical production bug|Users unable to login after latest deployment. Rollback may be needed.|Thursday, 12 February 2026 at 12:00:00 am|1
EISENHOWER_TEST|x-apple-reminder://B57D00ED-8EAB-482E-9963-6327A27AFCAC|Complete security audit report|Board meeting requires security compliance documentation.|Friday, 13 February 2026 at 12:00:00 am|1
EISENHOWER_TEST|x-apple-reminder://A887EB53-B39F-4DA2-B837-AF4294D6CE5D|Submit client proposal|Proposal for Project X includes: budget breakdown, timeline, team allocation, risk assessment. Client deadline is firm.|Saturday, 14 February 2026 at 12:00:00 am|5
EISENHOWER_TEST|x-apple-reminder://5DC3C429-3959-45ED-9C7B-860C06028A80|Review and merge pending PR|PR #247 has been waiting for 3 days. Blocks other team members.|Wednesday, 11 February 2026 at 12:00:00 am|1
EISENHOWER_TEST|x-apple-reminder://7E236B59-89DC-45D2-979C-C26DDA7B65DC|Prepare Q1 performance reviews|Review all team members, prepare feedback docs, schedule 1-on-1s.|Thursday, 19 February 2026 at 12:00:00 am|1
EISENHOWER_TEST|x-apple-reminder://6393356D-2B52-4048-B1FD-159F6338ED87|Refactor authentication module|Tech debt cleanup. Current code is hard to maintain. No urgent issues but should be addressed.|Thursday, 26 February 2026 at 12:00:00 am|5
EISENHOWER_TEST|x-apple-reminder://F4E5A001-59BB-4DCD-83FC-03FE67E255C9|Update team documentation|API docs, onboarding guide, and architecture diagrams need refresh.|Sunday, 22 February 2026 at 12:00:00 am|5
EISENHOWER_TEST|x-apple-reminder://B839E9A1-3934-40A0-ACBC-0AA14F550837|Renew SSL certificates|Certificates expire March 14. Renewal process takes 2-3 days.|Saturday, 14 March 2026 at 12:00:00 am|9
EISENHOWER_TEST|x-apple-reminder://FC379A43-E6F0-4956-89CA-472D4C4331A4|Respond to newsletter survey|missing value|Friday, 13 February 2026 at 12:00:00 am|0
EISENHOWER_TEST|x-apple-reminder://72BED27C-EF78-41CF-B468-CE0D3A03F0C6|RSVP to company social event|missing value|Saturday, 14 February 2026 at 12:00:00 am|9
EISENHOWER_TEST|x-apple-reminder://14718252-C3DB-40FC-8F0C-94A871F74D05|Water office plants|missing value|Thursday, 12 February 2026 at 12:00:00 am|0
EISENHOWER_TEST|x-apple-reminder://BA1BF736-06B4-435F-81F7-479726EAC40D|Organize digital files|missing value|missing value|0
EISENHOWER_TEST|x-apple-reminder://EF39D014-217A-4CF6-A758-1C7E105AD3B2|Read interesting article about AI|missing value|Sunday, 29 March 2026 at 12:00:00 am|0
EISENHOWER_TEST|x-apple-reminder://1CA08267-D62E-4A95-96C5-2A69E436591E|Clean out old browser bookmarks|Maybe someday...|missing value|0
EISENHOWER_TEST|x-apple-reminder://98CAD893-CCDF-44C0-8DFD-81C28A7160CC|🚀 Deploy new feature to staging|Feature branch: feat/user-dashboard|Friday, 13 February 2026 at 12:00:00 am|5
EISENHOWER_TEST|x-apple-reminder://40F630C5-662A-4A55-B648-B0F686388FD7|Investigate performance degradation in database queries affecting the user profile retrieval endpoint|Started noticing slowdowns around midnight|Friday, 13 February 2026 at 12:00:00 am|1
EISENHOWER_TEST|x-apple-reminder://56553BFD-2726-47C7-B4D8-EBCE1374885A|Fix: "Can't save" error (Windows/macOS)|Issue #123 - affects 15% of users|Thursday, 12 February 2026 at 12:00:00 am|1"""


def parse_due_date(date_str):
    """Parse AppleScript date string to YYYY-MM-DD"""
    if date_str == "missing value" or not date_str:
        return None

    # Parse "Thursday, 12 February 2026 at 12:00:00 am"
    try:
        parts = date_str.split(" at ")[0]  # Remove time portion
        date_obj = datetime.strptime(parts, "%A, %d %B %Y")
        return date_obj.date()
    except:
        return None


def clean_filename(title, max_length=50):
    """Generate clean filename from reminder title"""
    # Remove emojis
    title_clean = re.sub(r'[^\x00-\x7F]+', '', title)
    # Lowercase
    title_clean = title_clean.lower().strip()
    # Remove special chars except spaces and hyphens
    title_clean = re.sub(r'[^\w\s-]', '', title_clean)
    # Replace spaces with hyphens
    title_clean = re.sub(r'[\s_]+', '-', title_clean)
    # Remove multiple hyphens
    title_clean = re.sub(r'-+', '-', title_clean)
    # Truncate
    if len(title_clean) > max_length:
        title_clean = title_clean[:max_length].rstrip('-')
    return title_clean


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


def create_task_file(task_id, reminder):
    """Create task file from reminder data"""
    list_name, reminder_id, name, body, due_date_str, priority_str = reminder.split('|')

    priority_num = int(priority_str)
    priority = PRIORITY_MAP.get(priority_num, "low")
    due_date = parse_due_date(due_date_str)
    due_date_formatted = due_date.isoformat() if due_date else ""
    has_body = body != "missing value" and body != ""
    description = body if has_body else "No description provided"

    # Classify
    quadrant, is_urgent, is_important = classify_reminder(priority_num, due_date, has_body)

    # Generate filename
    filename = clean_filename(name)
    filepath = TASK_DIR / f"OUT-{task_id}-{filename}.md"

    # Create branch name
    branch_name = f"task/OUT-{task_id}-{filename}"

    # Create task content
    today_str = TODAY.isoformat()

    content = f"""---
id: OUT-{task_id}
title: {name}
type: task
status: todo
priority: {priority}
created: {today_str}
updated: {today_str}
assignee: Troy
branch: {branch_name}
source: reminder
reminder_id: "{reminder_id}"
reminder_list: "{list_name}"
due_date: "{due_date_formatted}"
eisenhower_quadrant: "{quadrant}"
eisenhower_urgent: {str(is_urgent).lower()}
eisenhower_important: {str(is_important).lower()}
---

# {name}

## Description
{description}

## Steps
- [ ] Review task details
- [ ] Complete task
- [ ] Mark as done

## Notes
Context, references, considerations.

## Source
Imported from macOS Reminders
- Original list: {list_name}
- Due date: {due_date_formatted or "None"}
- Priority: {priority_num} ({priority})

## Progress Log
- {today_str}: Imported from Reminders
"""

    return filepath, content, quadrant


# Process reminders
print("🔄 Processing reminders...")
print()

task_id = START_ID
quadrant_counts = {"q1": 0, "q2": 0, "q3": 0, "q4": 0}
created_tasks = []

for line in reminders_data.strip().split('\n'):
    if not line:
        continue

    filepath, content, quadrant = create_task_file(task_id, line)

    # Write file
    with open(filepath, 'w') as f:
        f.write(content)

    quadrant_counts[quadrant] += 1
    created_tasks.append(filepath.name)
    task_id += 1

# Print summary
print("✅ Reminders Import Complete")
print()
print(f"Imported: {len(created_tasks)} tasks")
print(f"- Q1 (Do First): {quadrant_counts['q1']} tasks")
print(f"- Q2 (Schedule): {quadrant_counts['q2']} tasks")
print(f"- Q3 (Delegate): {quadrant_counts['q3']} tasks")
print(f"- Q4 (Eliminate): {quadrant_counts['q4']} tasks")
print()
print("Files created:")
for task in created_tasks:
    print(f"  - {task}")
