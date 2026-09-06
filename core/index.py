"""The staging area (index).

This is intentionally much simpler than Git's real index format (which is
a packed binary structure with cache-invalidation stat data). MiniGit's
index is a flat JSON file: {relpath: {"hash": oid, "mode": mode}}. It
records exactly one thing -- "what would be committed if I ran `commit`
right now" -- decoupled from what happens to be on disk in the working
tree at that moment.
"""

from __future__ import annotations

import json
from pathlib import Path


class Index:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.entries: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            raw = self.path.read_text().strip()
            self.entries = json.loads(raw) if raw else {}
        else:
            self.entries = {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.entries, indent=2, sort_keys=True))

    def add(self, relpath: str, oid: str, mode: str = "100644") -> None:
        self.entries[relpath] = {"hash": oid, "mode": mode}

    def remove(self, relpath: str) -> None:
        self.entries.pop(relpath, None)

    def get(self, relpath: str) -> dict | None:
        return self.entries.get(relpath)

    def all_paths(self):
        return sorted(self.entries.keys())

    def clear(self) -> None:
        self.entries = {}
