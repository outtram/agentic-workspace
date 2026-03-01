"""Email handlers — /inbox and /email commands for the Command Centre."""


async def _noop(msg: str) -> None:
    """Default no-op progress callback."""


async def handle_inbox(progress=_noop) -> str:
    """Check inbox for recent emails."""
    await progress("[dim]Loading email config...[/]")
    try:
        from brain.core.config import Config
        from brain.mail.inbox import Inbox
    except ImportError:
        return "[red]Email modules not available[/]"

    config = Config.load()
    if not config.email_address or not config.email_app_password:
        return (
            "[bold red]Email not configured[/]\n"
            "Set OUTBOT_EMAIL_ADDRESS and OUTBOT_EMAIL_APP_PASSWORD in brain/.env"
        )

    inbox = Inbox(config.email_address, config.email_app_password)

    await progress("[dim]Connecting to Gmail...[/]")
    try:
        emails = await inbox.check(limit=10, unread_only=False)
    except Exception as e:
        hint = ""
        err = str(e)
        if "EOF" in err or "AUTHENTICATIONFAILED" in err:
            hint = "\n[dim]Hint: enable IMAP in Gmail Settings[/]"
        return f"[red]Inbox check failed: {e}[/]{hint}"

    if not emails:
        return "[dim]No recent emails in inbox[/]"

    lines = [f"[bold]Inbox[/] ({len(emails)} recent)\n"]
    for i, e in enumerate(emails, 1):
        name = e.sender_name or e.sender
        lines.append(f"[bold]{i}.[/] {name}")
        lines.append(f"   [#FF6B35]{e.subject}[/]")
        lines.append(f"   [dim]{e.date}[/]")
        preview = e.body[:100].replace("\n", " ") if e.body else "(no body)"
        lines.append(f"   {preview}\n")

    return "\n".join(lines)


async def handle_email_send(text: str, claude, progress=_noop) -> str:
    """Send an email — extract details via Claude then send."""
    await progress("[dim]Loading email config...[/]")
    try:
        from brain.core.config import Config
        from brain.core.events import EventBus
        from brain.mail.outbox import Outbox
    except ImportError:
        return "[red]Email modules not available[/]"

    config = Config.load()
    if not config.email_address or not config.email_app_password:
        return (
            "[bold red]Email not configured[/]\n"
            "Set OUTBOT_EMAIL_ADDRESS and OUTBOT_EMAIL_APP_PASSWORD in brain/.env"
        )

    await progress("[dim]Extracting email details...[/]")
    extraction = await claude.judge(
        prompt=text,
        system_prompt=(
            "Extract email details from the user's message. "
            "Reply in EXACTLY this format (one field per line):\n"
            "TO: <email address>\n"
            "SUBJECT: <subject line>\n"
            "BODY: <email body>\n\n"
            "If no recipient is specified, use TO: default\n"
            "If details are vague, make reasonable assumptions."
        ),
    )

    to_addr, subject, body = "", "", ""
    for line in extraction.strip().splitlines():
        line_s = line.strip()
        if line_s.upper().startswith("TO:"):
            to_addr = line_s[3:].strip()
        elif line_s.upper().startswith("SUBJECT:"):
            subject = line_s[8:].strip()
        elif line_s.upper().startswith("BODY:"):
            body = line_s[5:].strip()

    if to_addr.lower() == "default" or not to_addr:
        to_addr = config.email_default_to
        if not to_addr:
            return "[red]No recipient specified and OUTBOT_EMAIL_DEFAULT_TO not set[/]"

    if not subject:
        subject = "(no subject)"
    if not body:
        body = text

    await progress(f"[dim]Sending to {to_addr}...[/]")
    try:
        outbox = Outbox.from_config(config, event_bus=EventBus())
        await outbox.send(to=to_addr, subject=subject, body=body)
        return f"[bold #00D4AA]Email sent[/] to {to_addr}\nSubject: {subject}"
    except Exception as e:
        return f"[red]Email send failed: {e}[/]"
