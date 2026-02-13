import os
import click
from pathlib import Path
from reminders.core.manager import RemindersManager


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
@click.pass_context
def sync(ctx, dry_run):
    """Pull reminders from Reminders.app and create work items"""
    manager = ctx.obj['manager']

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
    quadrant_counts = {"q1": 0, "q2": 0, "q3": 0, "q4": 0}

    for reminder in reminders:
        # Skip if already imported
        if reminder["id"] in existing_reminder_ids:
            skipped_count += 1
            continue

        if dry_run:
            click.echo(f"Would import: {reminder['name']}")
            new_count += 1
            continue

        # Create work item from reminder
        work_item = manager.create_reminder(
            title=reminder["name"],
            due_date=reminder["due_date"],
            tags=reminder["tags"],
            priority=manager._map_apple_priority_to_string(reminder["priority"]),
            description=reminder["body"],
            list_name=reminder["list"]
        )

        quadrant_counts[work_item.eisenhower_quadrant] += 1
        new_count += 1

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
    click.echo(f"{'='*60}\n")


if __name__ == '__main__':
    main()
