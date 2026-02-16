"""Load OutBot personality and memory files."""

from pathlib import Path

# Approximate token count (1 token ~ 4 chars)
MAX_PERSONALITY_CHARS = 20000  # ~5000 tokens


class PersonalityLoader:
    """Loads and caches personality files for OutBot."""

    def __init__(self, memory_dir: str = ".claude/memory"):
        self.memory_dir = Path(memory_dir)
        self._cache: dict[str, str] = {}

    def load_file(self, filename: str) -> str:
        """Load a single memory file, with caching."""
        if filename in self._cache:
            return self._cache[filename]

        path = self.memory_dir / filename
        if not path.exists():
            return ""

        content = path.read_text(encoding="utf-8")
        self._cache[filename] = content
        return content

    def load_personality(self) -> str:
        """Load all personality files within token budget."""
        files = ["SOUL.md", "USER.md", "AGENTS.md"]
        sections: list[str] = []
        total_chars = 0

        for filename in files:
            content = self.load_file(filename)
            if not content:
                continue
            if total_chars + len(content) > MAX_PERSONALITY_CHARS:
                remaining = MAX_PERSONALITY_CHARS - total_chars
                content = content[:remaining] + "\n[...truncated]"
            sections.append(content)
            total_chars += len(content)
            if total_chars >= MAX_PERSONALITY_CHARS:
                break

        return "\n\n---\n\n".join(sections)

    def load_heartbeat_checklist(self) -> str:
        """Load the heartbeat checklist."""
        return self.load_file("HEARTBEAT.md")

    def clear_cache(self):
        """Clear the file cache (e.g., on session reset)."""
        self._cache.clear()
