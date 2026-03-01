"""Daily review handler — /daily runs the full pipeline with stage progress."""
import asyncio

from ..brain_logger import log_action


async def _noop(msg: str) -> None:
    """Default no-op progress callback."""


async def handle_daily(progress=_noop) -> str:
    """Run daily review pipeline with progress updates at each stage."""
    log_action("daily_review")
    loop = asyncio.get_running_loop()

    lines = ["[bold]Daily Review[/]\n"]

    # Stage 1: Sync reminders from macOS
    await progress("[dim]Importing reminders from macOS...[/]")
    try:
        from brain.workflows.daily_review import sync_reminders

        sync = await loop.run_in_executor(None, sync_reminders)
        if sync.get("error"):
            lines.append(f"[red]Reminders sync failed: {sync['error']}[/]")
        else:
            lines.append(
                f"Imported: [bold]{sync['new']}[/] new "
                f"({sync['skipped']} duplicates skipped)"
            )
    except Exception as e:
        lines.append(f"[red]Reminders sync failed: {e}[/]")

    # Stage 2: Count quadrants
    await progress("[dim]Counting tasks by quadrant...[/]")
    try:
        from brain.workflows.daily_review import get_quadrant_counts

        counts = await loop.run_in_executor(None, get_quadrant_counts)
        total = sum(counts.values())
        lines.append(f"\n[bold]Workload:[/] {total} tasks")
        lines.append(f"  [#FF6B35]Q1 Do First:[/] {counts['q1']}")
        lines.append(f"  [#00D4AA]Q2 Schedule:[/] {counts['q2']}")
        lines.append(f"  [dim]Q3 Delegate:[/] {counts['q3']}")
        lines.append(f"  [dim]Q4 Eliminate:[/] {counts['q4']}")
    except Exception as e:
        lines.append(f"[red]Quadrant counts failed: {e}[/]")

    # Stage 3: Check overdue
    await progress("[dim]Checking overdue tasks...[/]")
    try:
        from brain.workflows.daily_review import get_overdue_tasks

        urgency = await loop.run_in_executor(None, get_overdue_tasks)

        if urgency["overdue"]:
            lines.append(
                f"\n[bold red]OVERDUE ({len(urgency['overdue'])})[/]"
            )
            for t in urgency["overdue"][:5]:
                lines.append(
                    f"  [red]{t['id']}[/] {t['title']} "
                    f"({t['days_overdue']}d overdue)"
                )

        if urgency["due_today"]:
            lines.append(
                f"\n[bold #FF6B35]DUE TODAY ({len(urgency['due_today'])})[/]"
            )
            for t in urgency["due_today"]:
                lines.append(f"  [#FF6B35]{t['id']}[/] {t['title']}")

        if urgency["due_soon"]:
            lines.append(
                f"\n[bold]DUE SOON ({len(urgency['due_soon'])})[/]"
            )
            for t in urgency["due_soon"]:
                lines.append(
                    f"  {t['id']} {t['title']} (in {t['days']}d)"
                )
    except Exception as e:
        lines.append(f"[red]Overdue check failed: {e}[/]")

    # Stage 4: Check email inbox
    await progress("[dim]Checking email inbox...[/]")
    try:
        from brain.core.config import Config
        from brain.mail.inbox import Inbox

        config = Config.load()
        if config.email_address and config.email_app_password:
            inbox = Inbox(config.email_address, config.email_app_password)
            emails = await inbox.check(limit=5, unread_only=True)
            if emails:
                lines.append(
                    f"\n[bold]Email[/] ({len(emails)} unread)"
                )
                for e in emails[:5]:
                    name = e.sender_name or e.sender
                    subj = e.subject[:40] if e.subject else "(no subject)"
                    lines.append(f"  [#FF6B35]{name}[/] — {subj}")
            else:
                lines.append("\n[dim]Email: no unread messages[/]")
        else:
            lines.append("\n[dim]Email: not configured[/]")
    except Exception as e:
        lines.append(f"\n[dim]Email check failed: {e}[/]")

    # Stage 5: Generate dashboard
    await progress("[dim]Generating dashboard...[/]")
    try:
        from brain.workflows.daily_review import generate_dashboard

        dash = await loop.run_in_executor(None, generate_dashboard)
        if dash.get("filepath"):
            lines.append(f"\n[dim]Dashboard: {dash['filepath']}[/]")
            if dash.get("gist_updated"):
                lines.append("[dim]Mobile gist updated[/]")
    except Exception as e:
        lines.append(f"\n[dim]Dashboard generation failed: {e}[/]")

    return "\n".join(lines)
