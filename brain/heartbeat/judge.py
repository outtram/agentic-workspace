"""Importance judge - uses Claude to decide if findings warrant notification."""

import json
import logging

from brain.core.claude_client import ClaudeClient
from brain.core.models import JudgementResult

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """You are an importance judge for Troy's personal assistant.

Your job: Given a set of findings from a scheduled check, decide if Troy should be notified.

Rules:
- Only notify for genuinely important or time-sensitive items
- Meetings starting in <15 minutes = NOTIFY
- Overdue deadlines = NOTIFY
- New high-priority items = NOTIFY
- Routine events already acknowledged = SKIP
- Low-priority tasks with distant deadlines = SKIP
- "Nothing to report" = SKIP

Respond in JSON format ONLY (no markdown, no explanation outside the JSON):
{
  "should_notify": true/false,
  "message": "The WhatsApp message to send (if notifying). Use WhatsApp formatting: *bold*, bullets, short paragraphs.",
  "reasoning": "Brief explanation of why you decided to notify or not."
}"""


class ImportanceJudge:
    """Judges whether heartbeat findings warrant a notification to Troy."""

    def __init__(self, client: ClaudeClient | None = None):
        self.client = client or ClaudeClient()

    async def judge(self, findings: str, checklist: str) -> JudgementResult:
        """Judge the importance of heartbeat findings.

        Args:
            findings: Gathered data from integrations (reminders, calendar, etc.)
            checklist: The HEARTBEAT.md checklist content

        Returns:
            JudgementResult with should_notify, message, and reasoning
        """
        prompt = (
            "Here are the findings from this heartbeat check:\n\n"
            f"<findings>\n{findings}\n</findings>\n\n"
            f"<checklist>\n{checklist}\n</checklist>\n\n"
            "Based on the importance criteria in the checklist, "
            "should Troy be notified? Respond in the JSON format specified."
        )

        try:
            text = await self.client.judge(
                prompt=prompt,
                system_prompt=JUDGE_SYSTEM_PROMPT,
            )

            # Handle potential markdown code block wrapping
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]

            data = json.loads(text)
            return JudgementResult(
                should_notify=data.get("should_notify", False),
                message=data.get("message", ""),
                reasoning=data.get("reasoning", ""),
            )
        except Exception as e:
            logger.error("Importance judge failed: %s", e)
            return JudgementResult(
                should_notify=False,
                message="",
                reasoning=f"Judge error: {e}",
            )
