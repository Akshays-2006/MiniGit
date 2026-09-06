"""Content-addressable object storage.

Design:
    Every object is serialized as:

        b"<type> <len(body)>\\0<body>"

    and its identity (the object id, "oid") is the SHA-256 hex digest of
    THAT ENTIRE byte string -- header included. Hashing the header along
    with the body means:

      1. Two objects with identical bytes always get identical oids,
         regardless of type -- collisions across types are a non-issue in
         practice because the header disambiguates them structurally.
      2. Corruption (truncated body, tampered length) is detectable on
         read: we recompute size/hash and refuse to return bad data
         silently.

    Objects are stored at objects/<oid[:2]>/<oid[2:]>, matching Git's
    fan-out directory scheme -- it keeps any single directory from holding
    tens of thousands of entries as the repository grows.

    Writes are idempotent: if the target path already exists, we don't
    rewrite it. This is the mechanism by which MiniGit avoids storing
    redundant data -- an unchanged file staged in ten commits is written
    to disk exactly once.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .exceptions import InvalidObject, ObjectNotFound


class ObjectStore:
    def __init__(self, objects_dir: Path):
        self.objects_dir = Path(objects_dir)

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _path_for(self, oid: str) -> Path:
        if len(oid) < 3:
            raise InvalidObject(f"Malformed object id: {oid!r}")
        return self.objects_dir / oid[:2] / oid[2:]

    def write(self, obj_type: str, body: bytes) -> str:
        """Write an object of the given type and return its oid.

        No-op if an object with the same content already exists.
        """
        header = f"{obj_type} {len(body)}\0".encode()
        full = header + body
        oid = self.hash_bytes(full)
        path = self._path_for(oid)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(full)
        return oid

    def read(self, oid: str) -> tuple[str, bytes]:
        """Return (type, body) for the given oid, verifying integrity."""
        path = self._path_for(oid)
        if not path.exists():
            raise ObjectNotFound(f"Object '{oid}' not found in object store")
        full = path.read_bytes()
        if b"\0" not in full:
            raise InvalidObject(f"Corrupted object '{oid}': missing header terminator")
        header, _, body = full.partition(b"\0")
        try:
            obj_type, size_str = header.decode().split(" ", 1)
            expected_size = int(size_str)
        except ValueError as exc:
            raise InvalidObject(f"Corrupted object '{oid}': bad header") from exc
        if len(body) != expected_size:
            raise InvalidObject(
                f"Corrupted object '{oid}': expected {expected_size} bytes, got {len(body)}"
            )
        # Re-verify the hash itself matches the filename -- catches bit rot / edits.
        if self.hash_bytes(full) != oid:
            raise InvalidObject(f"Corrupted object '{oid}': hash mismatch")
        return obj_type, body

    def exists(self, oid: str) -> bool:
        return self._path_for(oid).exists()

    def count(self) -> int:
        if not self.objects_dir.exists():
            return 0
        return sum(1 for p in self.objects_dir.glob("*/*") if p.is_file())
