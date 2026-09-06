"""Commit objects: an immutable snapshot pointer + history link.

A commit is deliberately thin: a tree hash (the snapshot), zero or more
parent hashes (the history link -- more than one parent means this
commit is a merge), an author, a timestamp, and a message.

Because a commit's oid is a hash of all of this, INCLUDING its parents,
a commit's identity encodes its entire ancestry. Change one commit
anywhere in history and every descendant's hash changes too -- this is
what makes the commit graph tamper-evident, and it's also why history is
naturally a DAG rather than a mutable linked list: commits never get
edited in place, only new ones get appended.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Commit:
    tree: str
    parents: list[str] = field(default_factory=list)
    author: str = ""
    timestamp: float = 0.0
    message: str = ""

    def serialize(self) -> bytes:
        lines = [f"tree {self.tree}"]
        for parent in self.parents:
            lines.append(f"parent {parent}")
        lines.append(f"author {self.author} {self.timestamp}")
        lines.append("")  # blank line separates headers from message
        lines.append(self.message)
        return "\n".join(lines).encode()

    @classmethod
    def deserialize(cls, body: bytes) -> Commit:
        text = body.decode()
        lines = text.split("\n")
        tree = ""
        parents: list[str] = []
        author = ""
        timestamp = 0.0
        i = 0
        while i < len(lines):
            line = lines[i]
            if line == "":
                i += 1
                break
            if line.startswith("tree "):
                tree = line[len("tree "):]
            elif line.startswith("parent "):
                parents.append(line[len("parent "):])
            elif line.startswith("author "):
                rest = line[len("author "):]
                author, _, ts = rest.rpartition(" ")
                timestamp = float(ts)
            i += 1
        message = "\n".join(lines[i:])
        return cls(tree=tree, parents=parents, author=author, timestamp=timestamp, message=message)
