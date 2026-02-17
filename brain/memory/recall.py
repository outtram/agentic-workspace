"""Search past conversations and memory files for relevant context."""

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Patterns suggesting user wants historical context
_RECALL_PATTERNS = [
    r"\blast time\b",
    r"\bremember when\b",
    r"\bwhat did we (?:discuss|talk about|say)\b",
    r"\blast (?:week|session|chat|conversation)\b",
    r"\bpreviously\b",
    r"\bearlier\b(?!\s+today)",
    r"\byou (?:told|said|mentioned)\b",
    r"\bwe (?:talked|discussed|went over)\b",
    r"\bwhat do you (?:know|remember) about\b",
]

_RECALL_RE = [re.compile(p, re.IGNORECASE) for p in _RECALL_PATTERNS]

# Max chars to include as recall context (~1000 tokens)
MAX_RECALL_CHARS = 4000


def is_recall_trigger(text: str) -> bool:
    """Check if text references past conversations or stored knowledge."""
    return any(r.search(text) for r in _RECALL_RE)


def search_memory(query: str, memory_dir: str) -> list[dict]:
    """Search memory files and conversation archives for relevant content.

    Uses subprocess grep for simplicity — no vector search needed.

    Returns:
        List of {file, snippet} dicts, sorted by relevance (most recent first)
    """
    memory_path = Path(memory_dir)
    results = []

    # Extract keywords from query (skip common words)
    keywords = _extract_keywords(query)
    if not keywords:
        return []

    # Search conversation archives
    conversations_dir = Path("brain/store/conversations")
    if conversations_dir.exists():
        for kw in keywords[:3]:  # Top 3 keywords
            results.extend(_grep_dir(conversations_dir, kw))

    # Search memory files (USER.md, LEARNED.md, etc.)
    if memory_path.exists():
        for kw in keywords[:3]:
            results.extend(_grep_dir(memory_path, kw, pattern="*.md"))

    # Deduplicate by file+line
    seen = set()
    unique = []
    for r in results:
        key = (r["file"], r["snippet"][:80])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # Sort by filename descending (most recent conversations first)
    unique.sort(key=lambda r: r["file"], reverse=True)

    return unique[:6]  # Top 6 snippets max


def format_recall_context(results: list[dict]) -> str:
    """Format search results as XML context for the prompt.

    Keeps total under MAX_RECALL_CHARS.
    """
    if not results:
        return ""

    lines = ["<memory_recall>"]
    total = 0

    for r in results:
        filename = Path(r["file"]).name
        snippet = r["snippet"].strip()
        entry = f"[{filename}] {snippet}"

        if total + len(entry) > MAX_RECALL_CHARS:
            break

        lines.append(entry)
        total += len(entry)

    lines.append("</memory_recall>")
    return "\n".join(lines)


def _extract_keywords(text: str) -> list[str]:
    """Pull meaningful keywords from a query."""
    # Remove common filler words
    stop_words = {
        "the", "a", "an", "is", "was", "were", "are", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "about", "what", "when",
        "where", "who", "how", "why", "that", "this", "with", "from", "for",
        "and", "but", "or", "not", "you", "your", "we", "our", "me", "my",
        "it", "its", "they", "them", "their", "some", "any", "all", "each",
        "just", "also", "very", "really", "quite", "last", "time", "remember",
        "told", "said", "mentioned", "discussed", "talked", "know",
    }

    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    keywords = [w for w in words if w not in stop_words]

    # Deduplicate preserving order
    seen = set()
    unique = []
    for w in keywords:
        if w not in seen:
            seen.add(w)
            unique.append(w)

    return unique


def _grep_dir(directory: Path, keyword: str, pattern: str = "*.md") -> list[dict]:
    """Grep a directory for a keyword, returning matching snippets."""
    try:
        result = subprocess.run(
            ["grep", "-r", "-i", "-l", "--include", pattern, keyword, str(directory)],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return []

        results = []
        for filepath in result.stdout.strip().splitlines():
            if not filepath:
                continue
            # Get context lines around matches
            ctx = subprocess.run(
                ["grep", "-i", "-C", "2", keyword, filepath],
                capture_output=True, text=True, timeout=5,
            )
            if ctx.returncode == 0 and ctx.stdout.strip():
                # Take first match block (max 300 chars)
                snippet = ctx.stdout.strip()[:300]
                results.append({"file": filepath, "snippet": snippet})

        return results

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
