import os
import click
from pathlib import Path
from datetime import datetime
from reminders.core.manager import RemindersManager
from reminders.enrichment.ai_enricher import TaskEnricher


def _get_manager():
    """Create RemindersManager, respecting env vars for testing"""
    work_dir = os.environ.get("REMINDERS_WORK_DIR")
    use_mock = os.environ.get("REMINDERS_MOCK") == "1"

    kwargs = {}
    if work_dir:
        kwargs["work_dir"] = Path(work_dir)
    if use_mock:
        from reminders.tests.fixtures.mock_applescript import MockAppleScriptAdapter
        kwargs["applescript_adapter"] = MockAppleScriptAdapter()

    return RemindersManager(**kwargs)


@click.group()
@click.pass_context
def main(ctx):
    """Reminders Manager - Bi-directional sync with macOS Reminders"""
    ctx.ensure_object(dict)
    ctx.obj['manager'] = _get_manager()


@main.command()
@click.argument('title')
@click.option('--due', help='Due date (YYYY-MM-DD)')
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

    click.echo(f"Created {work_item.id}: {work_item.title}")
    if work_item.reminder_id:
        click.echo(f"Synced to Reminders.app")


@main.command('list')
@click.option('--tag', 'tags', multiple=True, help='Filter by tag')
@click.option('--q1', 'quadrant', flag_value='q1', help='Show Q1 (urgent & important)')
@click.option('--q2', 'quadrant', flag_value='q2', help='Show Q2 (not urgent but important)')
@click.option('--q3', 'quadrant', flag_value='q3', help='Show Q3 (urgent but not important)')
@click.option('--q4', 'quadrant', flag_value='q4', help='Show Q4 (not urgent & not important)')
@click.option('--status', default='todo', help='Filter by status')
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'compact', 'json']))
@click.pass_context
def list_cmd(ctx, tags, quadrant, status, output_format):
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
        click.echo("-" * 80)
        click.echo(f"{'ID':<10} {'Title':<40} {'Due':<12} {'Tags':<18}")
        click.echo("-" * 80)
        for item in items:
            tags_str = ", ".join(item.tags[:3])
            if len(item.tags) > 3:
                tags_str += "..."
            click.echo(f"{item.id:<10} {item.title[:38]:<40} {item.due_date or 'None':<12} {tags_str:<18}")
        click.echo("-" * 80)
        click.echo(f"{len(items)} reminders found")


@main.command()
@click.argument('work_item_id')
@click.pass_context
def complete(ctx, work_item_id):
    """Mark reminder as completed"""
    manager = ctx.obj['manager']

    try:
        manager.complete_reminder(work_item_id)
        click.echo(f"Completed {work_item_id}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@main.command()
@click.argument('work_item_id')
@click.option('--yes', is_flag=True, help='Skip confirmation')
@click.pass_context
def delete(ctx, work_item_id, yes):
    """Delete a reminder"""
    manager = ctx.obj['manager']

    if not yes:
        click.confirm(f"Delete {work_item_id}?", abort=True)

    try:
        manager.delete_reminder(work_item_id)
        click.echo(f"Deleted {work_item_id}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@main.command()
@click.argument('work_item_id')
@click.pass_context
def show(ctx, work_item_id):
    """Show detailed reminder info"""
    manager = ctx.obj['manager']

    item = manager.get_reminder(work_item_id)
    if not item:
        click.echo(f"Work item {work_item_id} not found", err=True)
        raise SystemExit(1)

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


@main.command()
@click.option('--dry-run', is_flag=True, help='Show what would be imported without creating files')
@click.option('--enrich', is_flag=True, help='Show enrichment suggestions for vague tasks')
@click.pass_context
def sync(ctx, dry_run, enrich):
    """Pull reminders from Reminders.app and create work items"""
    manager = ctx.obj['manager']
    enricher = TaskEnricher()

    # Fetch all reminders from Reminders.app
    click.echo("Fetching reminders from Reminders.app...")
    reminders = manager.applescript.fetch_all_reminders()

    if not reminders:
        click.echo("No active reminders found.")
        return

    # Get existing work items to check for duplicates
    existing_items = manager.list_reminders()
    existing_reminder_ids = {item.reminder_id for item in existing_items if item.reminder_id}

    new_count = 0
    skipped_count = 0
    vague_count = 0
    quadrant_counts = {"q1": 0, "q2": 0, "q3": 0, "q4": 0}
    vague_tasks = []

    for reminder in reminders:
        # Skip if already imported
        if reminder["id"] in existing_reminder_ids:
            skipped_count += 1
            continue

        if dry_run:
            click.echo(f"Would import: {reminder['name']}")
            new_count += 1
            continue

        # Import reminder as work item (no sync back to Reminders.app)
        work_item = manager.import_reminder(
            title=reminder["name"],
            reminder_id=reminder["id"],
            due_date=reminder["due_date"],
            tags=reminder["tags"],
            priority=manager._map_apple_priority_to_string(reminder["priority"]),
            description=reminder["body"],
            list_name=reminder["list"]
        )

        quadrant_counts[work_item.eisenhower_quadrant] += 1
        new_count += 1

        # Check if task is vague
        if enrich:
            enrichment = enricher.suggest_enrichment(
                title=work_item.title,
                description=work_item.description,
                due_date=work_item.due_date
            )
            if enrichment.get('needs_enrichment'):
                vague_count += 1
                vague_tasks.append((work_item.id, enrichment))

    # Report stats
    click.echo(f"\n{'='*60}")
    click.echo(f"Sync complete!")
    click.echo(f"{'='*60}")
    click.echo(f"New reminders imported: {new_count}")
    click.echo(f"Duplicates skipped: {skipped_count}")
    if new_count > 0:
        click.echo(f"\nBy quadrant:")
        click.echo(f"  🔥 Q1 (Do First): {quadrant_counts['q1']}")
        click.echo(f"  📅 Q2 (Schedule): {quadrant_counts['q2']}")
        click.echo(f"  🔀 Q3 (Delegate): {quadrant_counts['q3']}")
        click.echo(f"  🗑️  Q4 (Eliminate): {quadrant_counts['q4']}")

    # Show vague task warnings
    if enrich and vague_count > 0:
        click.echo(f"\n⚠️  Found {vague_count} vague task(s) that could be clearer:")
        for work_id, enrichment in vague_tasks[:3]:  # Show first 3
            click.echo(f"\n{enricher.format_enrichment_prompt(enrichment)}")
            click.echo(f"💡 Run: reminders enrich {work_id}")

        if vague_count > 3:
            click.echo(f"\n... and {vague_count - 3} more. Run 'reminders list' to see all tasks.")

    click.echo(f"{'='*60}\n")


@main.command()
@click.argument('work_item_id')
@click.pass_context
def enrich(ctx, work_item_id):
    """Make a vague task more actionable with AI suggestions"""
    manager = ctx.obj['manager']
    enricher = TaskEnricher()

    # Get the work item
    item = manager.get_reminder(work_item_id)
    if not item:
        click.echo(f"❌ Work item {work_item_id} not found", err=True)
        raise SystemExit(1)

    # Check if it needs enrichment
    enrichment = enricher.suggest_enrichment(
        title=item.title,
        description=item.description,
        due_date=item.due_date
    )

    if not enrichment.get('needs_enrichment'):
        click.echo(f"✅ Task looks clear: \"{item.title}\"")
        click.echo(f"No enrichment needed!")
        return

    # Show enrichment suggestions
    click.echo(enricher.format_enrichment_prompt(enrichment))

    # Ask if they want to update the task
    if not click.confirm("\n📝 Would you like to update this task now?"):
        click.echo("No worries! You can enrich it later.")
        return

    # Interactive enrichment
    click.echo("\nLet's make it actionable:")

    # Get new title
    new_title = click.prompt("New title (or press Enter to keep current)", default=item.title, show_default=False)

    # Get additional steps
    click.echo("\nAdd specific steps (one per line, empty line to finish):")
    steps = []
    while True:
        step = click.prompt("  - [ ]", default="", show_default=False)
        if not step:
            break
        steps.append(step)

    # Get additional tags
    suggested_tags = enrichment['suggested_improvements']['suggested_tags']
    if suggested_tags:
        click.echo(f"\nSuggested tags: {', '.join(suggested_tags)}")
        add_tags = click.confirm("Add these tags?")
        if add_tags:
            item.tags.extend(suggested_tags)
            item.tags = list(set(item.tags))  # Remove duplicates

    # Update the work item
    if new_title != item.title:
        item.title = new_title

    if steps:
        steps_text = "\n".join(f"- [ ] {step}" for step in steps)
        item.description = f"{item.description}\n\n## Steps\n{steps_text}".strip()

    # Save changes
    manager.workitems.write(item)
    click.echo(f"\n✅ Updated {work_item_id}!")
    click.echo(f"Title: {item.title}")
    if steps:
        click.echo(f"Added {len(steps)} steps")
    if suggested_tags:
        click.echo(f"Tags: {', '.join(item.tags)}")


@main.command()
@click.argument('work_item_id', required=False)
@click.option('--q1', 'show_q1', is_flag=True, help='Pick from Q1 tasks')
@click.pass_context
def progress(ctx, work_item_id, show_q1):
    """Help complete the next step of a task"""
    manager = ctx.obj['manager']

    # If no ID provided, show Q1 tasks or ask to pick one
    if not work_item_id:
        if show_q1:
            q1_items = manager.list_reminders(quadrant='q1', status='todo')
            if not q1_items:
                click.echo("🎉 No Q1 tasks! Great work!")
                return

            click.echo("🔥 Q1 Tasks (Urgent & Important):\n")
            for i, item in enumerate(q1_items[:5], 1):
                due_str = f"Due: {item.due_date}" if item.due_date else "No due date"
                click.echo(f"{i}. {item.id} - {item.title} ({due_str})")

            choice = click.prompt("\nWhich task to progress? (number or ID)", type=str)
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(q1_items):
                    work_item_id = q1_items[idx].id
            except ValueError:
                work_item_id = choice
        else:
            click.echo("💡 Use: reminders progress <work-item-id>")
            click.echo("Or: reminders progress --q1 (to pick from Q1 tasks)")
            return

    # Get the work item
    item = manager.get_reminder(work_item_id)
    if not item:
        click.echo(f"❌ Work item {work_item_id} not found", err=True)
        raise SystemExit(1)

    # Show current task
    click.echo(f"\n{'='*60}")
    click.echo(f"📋 {item.title}")
    click.echo(f"Priority: {item.priority} | Quadrant: {item.eisenhower_quadrant}")
    if item.due_date:
        due = datetime.fromisoformat(item.due_date.replace('Z', '+00:00')) if 'T' in item.due_date else datetime.fromisoformat(item.due_date)
        days_until = (due.date() - datetime.now().date()).days
        if days_until < 0:
            click.echo(f"⚠️  OVERDUE by {abs(days_until)} days!")
        elif days_until == 0:
            click.echo(f"⚠️  Due TODAY!")
        else:
            click.echo(f"Due in {days_until} days")
    click.echo(f"{'='*60}\n")

    # Parse description for unchecked steps
    unchecked_steps = []
    if item.description:
        import re
        lines = item.description.split('\n')
        for line in lines:
            if re.match(r'^\s*-\s*\[\s*\]\s+', line):
                step = re.sub(r'^\s*-\s*\[\s*\]\s+', '', line)
                unchecked_steps.append((line, step))

    if unchecked_steps:
        click.echo("Next steps:")
        for i, (_, step) in enumerate(unchecked_steps[:3], 1):
            click.echo(f"{i}. {step}")

        action = click.prompt("\nWhat would you like to do?",
                            type=click.Choice(['complete-step', 'add-note', 'mark-done', 'skip']),
                            default='complete-step')

        if action == 'complete-step':
            step_num = click.prompt("Which step?", type=int, default=1)
            if 1 <= step_num <= len(unchecked_steps):
                old_line, step_text = unchecked_steps[step_num - 1]
                new_line = old_line.replace('[ ]', '[x]')
                item.description = item.description.replace(old_line, new_line)
                manager.workitems.write(item)
                click.echo(f"✅ Marked step {step_num} as complete!")

        elif action == 'add-note':
            note = click.prompt("Add a note")
            item.description = f"{item.description}\n\n---\n**Update ({datetime.now().strftime('%Y-%m-%d')})**\n{note}"
            manager.workitems.write(item)
            click.echo("📝 Note added!")

        elif action == 'mark-done':
            if click.confirm("Mark entire task as complete?"):
                manager.complete_reminder(work_item_id)
                click.echo(f"✅ Completed {work_item_id}!")

    else:
        click.echo("No steps defined for this task.\n")
        action = click.prompt("What would you like to do?",
                            type=click.Choice(['add-steps', 'add-note', 'mark-done', 'skip']),
                            default='add-steps')

        if action == 'add-steps':
            click.echo("\nAdd steps (one per line, empty line to finish):")
            steps = []
            while True:
                step = click.prompt("  - [ ]", default="", show_default=False)
                if not step:
                    break
                steps.append(step)

            if steps:
                steps_text = "\n".join(f"- [ ] {step}" for step in steps)
                item.description = f"{item.description}\n\n## Steps\n{steps_text}".strip()
                manager.workitems.write(item)
                click.echo(f"✅ Added {len(steps)} steps!")

        elif action == 'add-note':
            note = click.prompt("Add a note")
            item.description = f"{item.description}\n\n---\n**Update ({datetime.now().strftime('%Y-%m-%d')})**\n{note}"
            manager.workitems.write(item)
            click.echo("📝 Note added!")

        elif action == 'mark-done':
            if click.confirm("Mark entire task as complete?"):
                manager.complete_reminder(work_item_id)
                click.echo(f"✅ Completed {work_item_id}!")


@main.command()
@click.pass_context
def nudge(ctx):
    """Check for overdue tasks and Q1 priorities (proactive reminders)"""
    manager = ctx.obj['manager']

    # Get all Q1 tasks
    q1_items = manager.list_reminders(quadrant='q1', status='todo')
    overdue = []
    due_today = []
    due_soon = []

    now = datetime.now().date()

    for item in q1_items:
        if not item.due_date:
            continue

        try:
            due = datetime.fromisoformat(item.due_date.replace('Z', '+00:00')).date() if 'T' in item.due_date else datetime.fromisoformat(item.due_date).date()
            days_until = (due - now).days

            if days_until < 0:
                overdue.append((item, abs(days_until)))
            elif days_until == 0:
                due_today.append(item)
            elif days_until <= 3:
                due_soon.append((item, days_until))
        except (ValueError, AttributeError):
            continue

    # Report findings
    total_nudges = len(overdue) + len(due_today) + len(due_soon)

    if total_nudges == 0:
        click.echo("✅ You're all caught up! No overdue or urgent Q1 tasks.")
        if q1_items:
            click.echo(f"\n📊 You have {len(q1_items)} Q1 task(s) in progress.")
            click.echo("💡 Run: reminders progress --q1")
        return

    click.echo("⚠️  URGENT ATTENTION NEEDED\n")

    # Overdue tasks (highest priority)
    if overdue:
        click.echo(f"🔴 OVERDUE ({len(overdue)} task{'s' if len(overdue) > 1 else ''}):")
        for item, days in sorted(overdue, key=lambda x: x[1], reverse=True)[:5]:
            click.echo(f"  • {item.id}: {item.title} (overdue by {days} day{'s' if days > 1 else ''})")
        click.echo()

    # Due today
    if due_today:
        click.echo(f"🟡 DUE TODAY ({len(due_today)} task{'s' if len(due_today) > 1 else ''}):")
        for item in due_today:
            click.echo(f"  • {item.id}: {item.title}")
        click.echo()

    # Due soon
    if due_soon:
        click.echo(f"🟠 DUE SOON ({len(due_soon)} task{'s' if len(due_soon) > 1 else ''}):")
        for item, days in sorted(due_soon, key=lambda x: x[1])[:5]:
            click.echo(f"  • {item.id}: {item.title} (in {days} day{'s' if days > 1 else ''})")
        click.echo()

    # Suggest action
    click.echo("💡 Recommended actions:")
    click.echo("  1. reminders progress --q1  (work on a Q1 task)")
    click.echo("  2. reminders complete <id>  (mark as done)")
    click.echo("  3. reminders show <id>      (review details)")

    # Pick most urgent for immediate action
    if overdue:
        most_urgent = max(overdue, key=lambda x: x[1])[0]
    elif due_today:
        most_urgent = due_today[0]
    else:
        most_urgent = due_soon[0][0]

    if click.confirm(f"\n🚀 Start working on: {most_urgent.title}?"):
        ctx.invoke(progress, work_item_id=most_urgent.id)


if __name__ == '__main__':
    main()
