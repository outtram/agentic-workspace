"""Daily review handler — /daily runs the full daily review pipeline."""
import asyncio

from ..brain_logger import log_action


async def handle_daily() -> str:
    """Run daily review pipeline in a thread (it's sync + slow)."""
    log_action("daily_review")

    try:
        from brain.workflows.daily_review import run_daily_review

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_daily_review)
        return result
    except Exception as e:
        return f"[red]Daily review failed: {e}[/]"
