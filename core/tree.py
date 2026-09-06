"""Tree objects: a snapshot of one directory level.

Each entry is (mode, type, hash, name). Entries are ALWAYS serialized in
name-sorted order -- this is the detail that makes trees content
addressable in a useful way: two directories with the same files always
produce the same tree hash, independent of filesystem iteration order.

Subdirectories are just entries whose type is "tree" and whose hash
points at another Tree object -- trees nest naturally into an arbitrarily
deep DAG without any special-casing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MODE_FILE = "100644"
MODE_DIR = "040000"


@dataclass
class TreeEntry:
    mode: str
    type: str  # "blob" | "tree"
    hash: str
    name: str


@dataclass
class Tree:
    entries: list[TreeEntry] = field(default_factory=list)

    def serialize(self) -> bytes:
        sorted_entries = sorted(self.entries, key=lambda e: e.name)
        lines = [f"{e.mode} {e.type} {e.hash} {e.name}" for e in sorted_entries]
        body = "\n".join(lines)
        if lines:
            body += "\n"
        return body.encode()

    @classmethod
    def deserialize(cls, body: bytes) -> Tree:
        entries = []
        text = body.decode()
        for line in text.splitlines():
            if not line:
                continue
            mode, type_, hash_, name = line.split(" ", 3)
            entries.append(TreeEntry(mode=mode, type=type_, hash=hash_, name=name))
        return cls(entries=entries)
