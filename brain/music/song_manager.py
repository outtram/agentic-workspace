"""Song manager — creates and loads songs with sequential MUS-XXX IDs.

Each song lives in its own folder under brain/music/songs/ with metadata
and session files.
"""
from __future__ import annotations

import random
from datetime import date
from pathlib import Path

import yaml

SONGS_DIR = Path(__file__).parent / "songs"
PATTERNS_DIR = Path(__file__).parent / "patterns"

# Fun name components — combined as adjective-noun
_ADJECTIVES = [
    "velvet", "neon", "cosmic", "liquid", "phantom", "chrome", "midnight",
    "feral", "molten", "spectral", "crimson", "golden", "frozen", "electric",
    "shadow", "astral", "savage", "silent", "thunder", "crystal", "binary",
    "haunted", "blazing", "ancient", "hollow", "wicked", "lucid", "primal",
    "volatile", "sonic", "hypnotic", "turbulent", "cryptic", "radiant",
]

_NOUNS = [
    "thunderclap", "platypus", "wombat", "aurora", "cascade", "sphinx",
    "nebula", "serpent", "citadel", "vortex", "monsoon", "coyote",
    "kraken", "phoenix", "glacier", "basilisk", "tempest", "minotaur",
    "quasar", "panther", "cyclone", "falcon", "inferno", "labyrinth",
    "chimera", "tsunami", "voltage", "mantis", "colossus", "anthem",
    "paradox", "raptor", "obsidian", "horizon", "renegade", "catalyst",
]


def _generate_name() -> str:
    """Generate a fun two-word name like 'velvet-thunderclap'."""
    return f"{random.choice(_ADJECTIVES)}-{random.choice(_NOUNS)}"


class SongManager:
    """Manages songs with sequential MUS-XXX IDs."""

    def __init__(self, songs_dir: Path | None = None, patterns_dir: Path | None = None):
        self.songs_dir = songs_dir or SONGS_DIR
        self.patterns_dir = patterns_dir or PATTERNS_DIR
        self.songs_dir.mkdir(parents=True, exist_ok=True)

    def next_id(self) -> str:
        """Scan existing songs and return the next sequential MUS-XXX ID."""
        existing = []
        for d in self.songs_dir.iterdir():
            if d.is_dir() and d.name.startswith("MUS-"):
                try:
                    num = int(d.name.split("-")[1])
                    existing.append(num)
                except (IndexError, ValueError):
                    continue
        next_num = max(existing, default=0) + 1
        return f"{next_num:03d}"

    def create_song(self, bpm: int = 128, key: str = "C", genre: str = "") -> dict:
        """Create a new song folder with metadata. Returns the song dict."""
        song_id = self.next_id()
        name = _generate_name()
        folder_name = f"MUS-{song_id}-{name}"
        song_dir = self.songs_dir / folder_name
        song_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "id": song_id,
            "name": name,
            "created": str(date.today()),
            "bpm": bpm,
            "key": key,
            "genre": genre,
            "tags": [],
            "patterns_used": [],
            "notes": "",
        }

        meta_path = song_dir / "song.yml"
        meta_path.write_text(yaml.dump(metadata, default_flow_style=False, allow_unicode=True))

        # Create empty session file
        session_path = song_dir / "session.tidal"
        session_path.write_text(f"-- {folder_name}\n-- Created {date.today()}\n\n")

        return metadata

    def load_song(self, song_id: str) -> dict | None:
        """Load a song's metadata by ID (just the number, e.g. '001')."""
        for d in self.songs_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"MUS-{song_id}-"):
                meta_path = d / "song.yml"
                if meta_path.exists():
                    return yaml.safe_load(meta_path.read_text())
        return None

    def save_session(self, song_id: str, tidal_code: str):
        """Write the full session code to session.tidal."""
        song_dir = self._find_song_dir(song_id)
        if song_dir:
            session_path = song_dir / "session.tidal"
            session_path.write_text(tidal_code)

    def append_session(self, song_id: str, code_line: str):
        """Append a line of code to the session file."""
        song_dir = self._find_song_dir(song_id)
        if song_dir:
            session_path = song_dir / "session.tidal"
            with open(session_path, "a") as f:
                f.write(f"{code_line}\n")

    def update_metadata(self, song_id: str, **kwargs):
        """Update specific fields in song.yml."""
        song_dir = self._find_song_dir(song_id)
        if not song_dir:
            return
        meta_path = song_dir / "song.yml"
        if not meta_path.exists():
            return
        metadata = yaml.safe_load(meta_path.read_text()) or {}
        metadata.update(kwargs)
        meta_path.write_text(yaml.dump(metadata, default_flow_style=False, allow_unicode=True))

    def list_songs(self) -> list[dict]:
        """Return all songs sorted by ID."""
        songs = []
        for d in sorted(self.songs_dir.iterdir()):
            if d.is_dir() and d.name.startswith("MUS-"):
                meta_path = d / "song.yml"
                if meta_path.exists():
                    meta = yaml.safe_load(meta_path.read_text())
                    if meta:
                        songs.append(meta)
        return songs

    def save_pattern(self, category: str, name: str, code: str, **kwargs):
        """Save a reusable pattern to patterns/<category>/<name>.yml."""
        cat_dir = self.patterns_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        pattern = {
            "name": name,
            "category": category,
            "code": code,
            **kwargs,
        }
        path = cat_dir / f"{name}.yml"
        path.write_text(yaml.dump(pattern, default_flow_style=False, allow_unicode=True))

    def load_patterns(self, category: str) -> list[dict]:
        """Load all patterns from a category directory."""
        cat_dir = self.patterns_dir / category
        if not cat_dir.exists():
            return []
        patterns = []
        for f in sorted(cat_dir.glob("*.yml")):
            data = yaml.safe_load(f.read_text())
            if data:
                patterns.append(data)
        return patterns

    def _find_song_dir(self, song_id: str) -> Path | None:
        """Find a song directory by its numeric ID."""
        for d in self.songs_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"MUS-{song_id}-"):
                return d
        return None
