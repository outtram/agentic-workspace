"""End-of-session reflection — observe patterns and evolve memory."""

import logging
from datetime import date
from pathlib import Path

from brain.core.claude_client import ClaudeClient
from brain.core.models import Message

logger = logging.getLogger(__name__)

# Max new observations per reflection cycle
MAX_OBSERVATIONS = 3

REFLECTION_SECTION = "## Observed Patterns"

REFLECTION_PROMPT = """\
You are analysing recent conversations between Troy and OutBot.
Identify NEW patterns about Troy — preferences, habits, communication style, or interests.

Rules:
- Only list genuinely new observations (not already in existing notes)
- Max {max_obs} observations
- Each observation should be a single concise sentence
- Focus on behavioural patterns, not conversation content
- Reply with ONLY the observations, one per line, no numbers or bullets
- If nothing new to observe, reply with exactly: NOTHING_NEW

Existing notes about Troy:
{existing}

Recent conversation:
{conversation}"""


async def reflect_on_session(
    messages: list[Message],
    memory_dir: str,
    claude: ClaudeClient,
) -> list[str]:
    """Analyse recent messages and return new observations about Troy.

    Args:
        messages: Recent conversation messages
        memory_dir: Path to .claude/memory/
        claude: ClaudeClient for haiku calls

    Returns:
        List of new observations that were written to USER.md
    """
    if len(messages) < 4:
        logger.debug("Too few messages (%d) for reflection", len(messages))
        return []

    memory_path = Path(memory_dir)

    # Load existing USER.md content for dedup
    user_md = memory_path / "USER.md"
    existing = user_md.read_text(encoding="utf-8") if user_md.exists() else ""

    # Format recent conversation for analysis
    conversation = "\n".join(
        f"{m.sender_name}: {m.content}" for m in messages[-20:]
    )

    # Ask haiku to identify patterns
    prompt = REFLECTION_PROMPT.format(
        max_obs=MAX_OBSERVATIONS,
        existing=existing[:2000],
        conversation=conversation[:3000],
    )

    result = await claude.judge(prompt=prompt)

    if "NOTHING_NEW" in result:
        logger.debug("Reflection found nothing new")
        return []

    # Parse observations
    observations = _parse_observations(result, existing)

    if not observations:
        return []

    # Write to USER.md
    _write_observations(user_md, observations)
    logger.info("Reflection added %d observations", len(observations))

    return observations


def _parse_observations(result: str, existing: str) -> list[str]:
    """Parse and deduplicate observations from Claude's response."""
    existing_lower = existing.lower()
    observations = []

    for line in result.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Strip leading bullets/numbers
        line = line.lstrip("0123456789.-•) ").strip()
        if not line:
            continue

        # Dedup: skip if substantially similar to existing content
        # Check if any 4+ word phrase from the observation appears in existing
        words = line.lower().split()
        if len(words) >= 4:
            phrase = " ".join(words[:4])
            if phrase in existing_lower:
                continue

        observations.append(line)

        if len(observations) >= MAX_OBSERVATIONS:
            break

    return observations


def _write_observations(user_md: Path, observations: list[str]):
    """Append observations to the ## Observed Patterns section of USER.md."""
    today = date.today().isoformat()

    if not user_md.exists():
        content = ""
    else:
        content = user_md.read_text(encoding="utf-8")

    lines = [f"- {obs} (observed {today})" for obs in observations]
    new_content = "\n".join(lines)

    if REFLECTION_SECTION in content:
        # Find end of section and append
        idx = content.index(REFLECTION_SECTION) + len(REFLECTION_SECTION)
        next_section = content.find("\n## ", idx)
        if next_section == -1:
            if not content.endswith("\n"):
                content += "\n"
            content += new_content + "\n"
        else:
            content = content[:next_section] + new_content + "\n" + content[next_section:]
    else:
        if not content.endswith("\n"):
            content += "\n"
        content += f"\n{REFLECTION_SECTION}\n{new_content}\n"

    user_md.write_text(content, encoding="utf-8")
