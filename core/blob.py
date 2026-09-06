"""Blob objects: the raw contents of a single file, nothing else.

A blob has no filename, no permissions, no metadata -- that information
lives one layer up, in the tree entry that points at the blob. This is
why renaming a file to an identical sibling costs nothing: the blob
itself is unchanged, only the tree entry's name differs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Blob:
    content: bytes

    def serialize(self) -> bytes:
        return self.content

    @classmethod
    def deserialize(cls, body: bytes) -> Blob:
        return cls(content=body)
