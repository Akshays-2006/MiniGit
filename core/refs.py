"""HEAD and refs/heads/* management.

A branch is nothing but a text file at refs/heads/<name> containing a
commit oid -- creating a branch is a single file write, never a copy of
repository content. This is the whole reason branching is cheap: the
branch *is* the pointer, not a duplicate of anything it points at.

HEAD is a symbolic reference: refs/heads/main-ish. It stores the string
"ref: refs/heads/<branch>" rather than a raw commit hash, so that
committing on the current branch only requires updating one ref file
(the branch's), and HEAD automatically "follows" because it's defined
in terms of the branch, not a snapshot of it.

Detached HEAD (HEAD holding a raw commit hash directly) is supported at
the read level here for robustness, but MiniGit's CLI/API never
constructs one -- it's explicitly out of scope for the MVP.
"""

from __future__ import annotations

from pathlib import Path

from .exceptions import BranchNotFound

HEADS_PREFIX = "refs/heads/"


class RefManager:
    def __init__(self, minigit_dir: Path):
        self.minigit_dir = Path(minigit_dir)
        self.heads_dir = self.minigit_dir / "refs" / "heads"
        self.head_path = self.minigit_dir / "HEAD"

    # ---- branch refs ----
    def branch_exists(self, name: str) -> bool:
        return (self.heads_dir / name).is_file()

    def create_branch(self, name: str, commit_oid: str) -> None:
        path = self.heads_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(commit_oid)

    def set_branch_commit(self, name: str, commit_oid: str) -> None:
        path = self.heads_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(commit_oid)

    def get_branch_commit(self, name: str) -> str:
        path = self.heads_dir / name
        if not path.is_file():
            raise BranchNotFound(f"Branch '{name}' not found")
        return path.read_text().strip()

    def delete_branch(self, name: str) -> None:
        path = self.heads_dir / name
        if not path.is_file():
            raise BranchNotFound(f"Branch '{name}' not found")
        path.unlink()
        # Clean up now-empty parent directories (e.g. "feature/" after
        # deleting the last "feature/*" branch), mirroring Git's behavior.
        parent = path.parent
        while parent != self.heads_dir and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent

    def list_branches(self) -> list[str]:
        """Branch names can contain '/' (e.g. 'feature/auth'), stored as
        nested files under refs/heads/ exactly like Git does -- so listing
        means a recursive walk, not a flat directory listing."""
        if not self.heads_dir.exists():
            return []
        return sorted(
            p.relative_to(self.heads_dir).as_posix()
            for p in self.heads_dir.rglob("*")
            if p.is_file()
        )

    # ---- HEAD ----
    def get_head_ref(self) -> str:
        content = self.head_path.read_text().strip()
        if content.startswith("ref: "):
            return content[len("ref: "):]
        return content  # detached HEAD: raw commit hash

    def set_head_ref(self, ref: str) -> None:
        self.head_path.write_text(f"ref: {ref}\n")

    def get_current_branch(self) -> str:
        ref = self.get_head_ref()
        if ref.startswith(HEADS_PREFIX):
            return ref[len(HEADS_PREFIX):]
        return ref  # detached

    def get_head_commit(self) -> str | None:
        ref = self.get_head_ref()
        if ref.startswith(HEADS_PREFIX):
            branch = ref[len(HEADS_PREFIX):]
            path = self.heads_dir / branch
            if not path.exists():
                return None
            content = path.read_text().strip()
            return content or None
        return ref or None
