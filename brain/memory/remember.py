"""Handle 'remember this' and 'forget that' memory triggers."""

import logging
import re
from datetime import date
from pathlib import Path

from brain.core.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

# Patterns that indicate the user wants OutBot to remember something
_REMEMBER_PATTERNS = [
    r"\bremember\b(?!\s+(?:when|that time|the time|what|how|where|who|why))",
    r"\bdon'?t forget\b",
    r"\bnote that\b",
    r"\bkeep in mind\b",
]

# Patterns that indicate the user wants OutBot to forget something
_FORGET_PATTERNS = [
    r"\bforget\b(?!\s+(?:about it|it)$)",
    r"\bstop remembering\b",
    r"\bremove (?:the )?(?:memory|note)\b",
]

# Compiled regexes
_REMEMBER_RE = [re.compile(p, re.IGNORECASE) for p in _REMEMBER_PATTERNS]
_FORGET_RE = [re.compile(p, re.IGNORECASE) for p in _FORGET_PATTERNS]


def is_memory_trigger(text: str) -> bool:
    """Check if text contains a memory trigger (remember or forget)."""
    return is_remember_trigger(text) or is_forget_trigger(text)


def is_remember_trigger(text: str) -> bool:
    """Check if text asks OutBot to remember something."""
    # Reject questions — these are recall requests, not storage
    stripped = text.strip()
    if stripped.endswith("?"):
        return False
    if re.match(r"^(what|do|can|how|where|who|why)\b", stripped, re.IGNORECASE):
        return False

    return any(r.search(text) for r in _REMEMBER_RE)


def is_forget_trigger(text: str) -> bool:
    """Check if text asks OutBot to forget something."""
    return any(r.search(text) for r in _FORGET_RE)


async def extract_memory(text: str, claude: ClaudeClient) -> dict:
    """Use haiku to extract what to remember and classify it.

    Returns:
        dict with keys: content, category (user_pref | personality | fact)
    """
    result = await claude.judge(
        prompt=text,
        system_prompt=(
            "Extract the thing the user wants remembered. "
            "Reply with EXACTLY two lines:\n"
            "CONTENT: <what to remember>\n"
            "CATEGORY: <user_pref|personality|fact>\n\n"
            "user_pref = personal preferences (likes, dislikes, habits)\n"
            "personality = how they want you to behave\n"
            "fact = general information or notes\n\n"
            "Examples:\n"
            "'remember I hate morning meetings' → CONTENT: Hates morning meetings / CATEGORY: user_pref\n"
            "'remember the server IP is 10.0.0.5' → CONTENT: Server IP is 10.0.0.5 / CATEGORY: fact\n"
            "'remember to always be brief' → CONTENT: Always be brief / CATEGORY: personality"
        ),
    )

    content = ""
    category = "fact"
    for line in result.strip().splitlines():
        if line.upper().startswith("CONTENT:"):
            content = line.split(":", 1)[1].strip()
        elif line.upper().startswith("CATEGORY:"):
            cat = line.split(":", 1)[1].strip().lower()
            if cat in ("user_pref", "personality", "fact"):
                category = cat

    if not content:
        content = text  # Fallback: store the raw text

    return {"content": content, "category": category}


def write_memory(entry: dict, memory_dir: str) -> str:
    """Append a memory entry to the appropriate file.

    Args:
        entry: dict with 'content' and 'category'
        memory_dir: path to .claude/memory/

    Returns:
        Summary string of what was saved
    """
    memory_path = Path(memory_dir)
    today = date.today().isoformat()
    line = f"- {entry['content']} (learned {today})"

    if entry["category"] == "user_pref":
        _append_to_section(memory_path / "USER.md", "Learned", line)
    else:
        _append_to_learned(memory_path / "LEARNED.md", entry["category"], line)

    logger.info("Memory saved: %s → %s", entry["content"], entry["category"])
    return entry["content"]


def _append_to_section(filepath: Path, section: str, line: str):
    """Append a line to a specific ## section in a markdown file, creating it if needed."""
    if not filepath.exists():
        filepath.write_text(f"## {section}\n{line}\n", encoding="utf-8")
        return

    content = filepath.read_text(encoding="utf-8")
    header = f"## {section}"

    if header in content:
        # Append after the section header and existing entries
        idx = content.index(header) + len(header)
        # Find the end of this section (next ## or end of file)
        next_section = content.find("\n## ", idx)
        if next_section == -1:
            # Append at end of file
            if not content.endswith("\n"):
                content += "\n"
            content += f"{line}\n"
        else:
            # Insert before the next section
            content = content[:next_section] + f"{line}\n" + content[next_section:]
    else:
        # Add section at end of file
        if not content.endswith("\n"):
            content += "\n"
        content += f"\n{header}\n{line}\n"

    filepath.write_text(content, encoding="utf-8")


def _append_to_learned(filepath: Path, category: str, line: str):
    """Append to LEARNED.md, creating the file if needed."""
    if not filepath.exists():
        filepath.write_text(f"# Learned Memories\n\n{line}\n", encoding="utf-8")
        return

    content = filepath.read_text(encoding="utf-8")
    if not content.endswith("\n"):
        content += "\n"
    content += f"{line}\n"
    filepath.write_text(content, encoding="utf-8")


async def forget_memory(text: str, memory_dir: str, claude: ClaudeClient) -> bool:
    """Find and remove a matching memory entry.

    Returns:
        True if an entry was found and removed
    """
    # Ask haiku what to forget
    result = await claude.judge(
        prompt=text,
        system_prompt=(
            "The user wants to forget/remove a previously stored memory. "
            "Extract the key phrase to search for. "
            "Reply with EXACTLY one line:\n"
            "SEARCH: <key phrase to match>"
        ),
    )

    search = ""
    for line in result.strip().splitlines():
        if line.upper().startswith("SEARCH:"):
            search = line.split(":", 1)[1].strip().lower()
            break

    if not search:
        return False

    memory_path = Path(memory_dir)
    removed = False

    # Search in USER.md and LEARNED.md
    for filepath in [memory_path / "USER.md", memory_path / "LEARNED.md"]:
        if not filepath.exists():
            continue

        lines = filepath.read_text(encoding="utf-8").splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("- ") and search in line.lower():
                logger.info("Forgot memory: %s", line.strip())
                removed = True
                continue
            new_lines.append(line)

        if removed:
            filepath.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            break

    return removed
