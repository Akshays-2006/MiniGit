"""Repository: orchestrates the object store, index and refs.

This is the single entry point both the CLI and (later) the REST API call
into -- neither of them should ever touch ObjectStore/Index/RefManager
directly. That's the architectural rule that keeps business logic from
being duplicated between the two front ends.
"""

from __future__ import annotations

import time
from pathlib import Path

from .blob import Blob
from .commit import Commit
from .exceptions import (
    BranchAlreadyExists,
    InvalidCommit,
    InvalidRepository,
    NothingToCommit,
    PathspecError,
    RepositoryNotFound,
)
from .index import Index
from .objects import ObjectStore
from .refs import RefManager
from .tree import MODE_DIR, MODE_FILE, Tree, TreeEntry

MINIGIT_DIR = ".minigit"
DEFAULT_AUTHOR = "MiniGit User <user@example.com>"
DEFAULT_BRANCH = "main"


class Repository:
    def __init__(self, worktree: Path):
        self.worktree = Path(worktree).resolve()
        self.minigit_dir = self.worktree / MINIGIT_DIR
        self.objects_dir = self.minigit_dir / "objects"
        self.store = ObjectStore(self.objects_dir)
        self.refs = RefManager(self.minigit_dir)
        self.index = Index(self.minigit_dir / "index")

    # ---------------------------------------------------------------
    # Repository lifecycle
    # ---------------------------------------------------------------
    @classmethod
    def init(cls, path: Path) -> Repository:
        worktree = Path(path).resolve()
        minigit_dir = worktree / MINIGIT_DIR
        if minigit_dir.exists():
            raise InvalidRepository(f"Repository already exists at {worktree}")
        worktree.mkdir(parents=True, exist_ok=True)
        (minigit_dir / "objects").mkdir(parents=True)
        (minigit_dir / "refs" / "heads").mkdir(parents=True)
        (minigit_dir / "HEAD").write_text(f"ref: refs/heads/{DEFAULT_BRANCH}\n")
        (minigit_dir / "index").write_text("{}")
        (minigit_dir / "config").write_text(f'{{"author": "{DEFAULT_AUTHOR}"}}\n')
        return cls(worktree)

    @classmethod
    def find(cls, start: Path | None = None) -> Repository:
        cur = Path(start or Path.cwd()).resolve()
        for candidate in [cur, *cur.parents]:
            if (candidate / MINIGIT_DIR).exists():
                return cls(candidate)
        raise RepositoryNotFound("Not a MiniGit repository (or any parent up to root)")

    # ---------------------------------------------------------------
    # Working tree helpers
    # ---------------------------------------------------------------
    def _iter_worktree_files(self) -> list[str]:
        if not self.worktree.exists():
            return []
        results = []
        for path in self.worktree.rglob("*"):
            if MINIGIT_DIR in path.parts:
                continue
            if path.is_file():
                results.append(path.relative_to(self.worktree).as_posix())
        return results

    def _read_worktree_file(self, relpath: str) -> bytes:
        return (self.worktree / relpath).read_bytes()

    # ---------------------------------------------------------------
    # Object helpers
    # ---------------------------------------------------------------
    def get_commit(self, oid: str) -> Commit:
        obj_type, body = self.store.read(oid)
        if obj_type != "commit":
            raise InvalidCommit(f"Object '{oid}' is not a commit (found '{obj_type}')")
        return Commit.deserialize(body)

    def get_tree(self, oid: str) -> Tree:
        obj_type, body = self.store.read(oid)
        if obj_type != "tree":
            raise InvalidCommit(f"Object '{oid}' is not a tree (found '{obj_type}')")
        return Tree.deserialize(body)

    def get_blob(self, oid: str) -> Blob:
        obj_type, body = self.store.read(oid)
        if obj_type != "blob":
            raise InvalidCommit(f"Object '{oid}' is not a blob (found '{obj_type}')")
        return Blob.deserialize(body)

    def _flatten_tree(self, tree_oid: str, prefix: str = "") -> dict[str, str]:
        """Recursively flatten a tree into {relpath: blob_oid}."""
        result: dict[str, str] = {}
        tree = self.get_tree(tree_oid)
        for entry in tree.entries:
            path = f"{prefix}{entry.name}"
            if entry.type == "tree":
                result.update(self._flatten_tree(entry.hash, prefix=f"{path}/"))
            else:
                result[path] = entry.hash
        return result

    def _get_head_tree_files(self) -> dict[str, str]:
        head_commit = self.refs.get_head_commit()
        if head_commit is None:
            return {}
        commit = self.get_commit(head_commit)
        return self._flatten_tree(commit.tree)

    def _build_tree_from_index(self) -> str:
        """Build a nested Tree object graph from the flat index and return
        the root tree's oid. Identical subtrees across commits automatically
        collapse to the same oid, since tree hashing is content-addressable."""
        root: dict = {}
        for relpath, entry in self.index.entries.items():
            parts = relpath.split("/")
            node = root
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = entry["hash"]

        def write_tree(node: dict) -> str:
            entries = []
            for name, value in node.items():
                if isinstance(value, dict):
                    sub_oid = write_tree(value)
                    entries.append(TreeEntry(mode=MODE_DIR, type="tree", hash=sub_oid, name=name))
                else:
                    entries.append(TreeEntry(mode=MODE_FILE, type="blob", hash=value, name=name))
            tree = Tree(entries=entries)
            return self.store.write("tree", tree.serialize())

        return write_tree(root)

    # ---------------------------------------------------------------
    # Staging
    # ---------------------------------------------------------------
    def add_path(self, target: str) -> list[str]:
        """Stage a file or every file under a directory. Returns staged relpaths."""
        target_path = self.worktree / target
        if not target_path.exists():
            raise PathspecError(f"pathspec '{target}' did not match any files")

        if target_path.is_file():
            relpaths = [target_path.relative_to(self.worktree).as_posix()]
        else:
            relpaths = [
                p.relative_to(self.worktree).as_posix()
                for p in target_path.rglob("*")
                if p.is_file() and MINIGIT_DIR not in p.parts
            ]

        for relpath in relpaths:
            content = self._read_worktree_file(relpath)
            blob = Blob(content)
            oid = self.store.write("blob", blob.serialize())
            self.index.add(relpath, oid)
        self.index.save()
        return relpaths

    # ---------------------------------------------------------------
    # Status
    # ---------------------------------------------------------------
    def status(self) -> dict:
        working_files = set(self._iter_worktree_files())
        staged_paths = set(self.index.all_paths())
        head_tree = self._get_head_tree_files()

        staged: set = set()
        modified_unstaged: set = set()
        untracked: set = set()
        deleted: set = set()

        for relpath in working_files:
            content = self._read_worktree_file(relpath)
            current_hash = self.store.hash_bytes(f"blob {len(content)}\0".encode() + content)
            index_entry = self.index.get(relpath)
            if index_entry is None:
                if relpath in head_tree:
                    if head_tree[relpath] != current_hash:
                        modified_unstaged.add(relpath)
                else:
                    untracked.add(relpath)
            else:
                if index_entry["hash"] != current_hash:
                    modified_unstaged.add(relpath)

        for relpath in staged_paths:
            head_hash = head_tree.get(relpath)
            index_hash = self.index.get(relpath)["hash"]
            if head_hash != index_hash:
                staged.add(relpath)

        # Deleted: tracked (by HEAD or index) but missing from the working tree.
        tracked_paths = set(head_tree.keys()) | staged_paths
        for relpath in tracked_paths:
            if relpath not in working_files:
                deleted.add(relpath)

        return {
            "branch": self.refs.get_current_branch(),
            "staged": sorted(staged),
            "modified_unstaged": sorted(modified_unstaged),
            "untracked": sorted(untracked),
            "deleted": sorted(deleted),
        }

    def is_clean(self) -> bool:
        s = self.status()
        return not (s["staged"] or s["modified_unstaged"] or s["deleted"])

    # ---------------------------------------------------------------
    # Commit
    # ---------------------------------------------------------------
    def commit(self, message: str, author: str = DEFAULT_AUTHOR) -> str:
        if not self.index.entries:
            raise NothingToCommit("Nothing to commit: the staging area is empty")

        tree_oid = self._build_tree_from_index()
        head_commit_oid = self.refs.get_head_commit()
        parents = [head_commit_oid] if head_commit_oid else []

        if head_commit_oid is not None:
            prev_commit = self.get_commit(head_commit_oid)
            if prev_commit.tree == tree_oid:
                raise NothingToCommit("Nothing to commit: working tree matches HEAD")

        commit_obj = Commit(
            tree=tree_oid,
            parents=parents,
            author=author,
            timestamp=time.time(),
            message=message,
        )
        commit_oid = self.store.write("commit", commit_obj.serialize())

        branch = self.refs.get_current_branch()
        if not self.refs.branch_exists(branch):
            # First commit ever: refs/heads/main doesn't exist until now.
            self.refs.create_branch(branch, commit_oid)
        else:
            self.refs.set_branch_commit(branch, commit_oid)
        return commit_oid

    # ---------------------------------------------------------------
    # Log / history (DAG traversal)
    # ---------------------------------------------------------------
    def log(self, start: str | None = None) -> list[tuple[str, Commit]]:
        """Traverse the commit DAG from `start` (default: HEAD) via all
        parent edges, returning (oid, commit) pairs newest-first.

        This is a graph traversal, not a linked-list walk: a commit may
        have multiple parents (merges), so we track visited oids to avoid
        revisiting shared ancestors reachable through more than one path.
        """
        start = start or self.refs.get_head_commit()
        if start is None:
            return []
        visited = set()
        result: list[tuple[str, Commit]] = []
        stack = [start]
        while stack:
            oid = stack.pop()
            if oid in visited:
                continue
            visited.add(oid)
            commit = self.get_commit(oid)
            result.append((oid, commit))
            stack.extend(commit.parents)
        result.sort(key=lambda pair: pair[1].timestamp, reverse=True)
        return result

    def log_all_branches(self) -> list[tuple[str, Commit]]:
        """Union of every branch tip's ancestry -- the commit set a network
        graph view needs (git log --all), rather than just HEAD's history.
        """
        visited = set()
        result: list[tuple[str, Commit]] = []
        stack = [self.refs.get_branch_commit(name) for name in self.list_branches()]
        while stack:
            oid = stack.pop()
            if oid in visited:
                continue
            visited.add(oid)
            commit = self.get_commit(oid)
            result.append((oid, commit))
            stack.extend(commit.parents)
        result.sort(key=lambda pair: pair[1].timestamp, reverse=True)
        return result

    # ---------------------------------------------------------------
    # Branches
    # ---------------------------------------------------------------
    def create_branch(self, name: str, start_commit: str | None = None) -> None:
        if self.refs.branch_exists(name):
            raise BranchAlreadyExists(f"Branch '{name}' already exists")
        commit_oid = start_commit or self.refs.get_head_commit()
        if commit_oid is None:
            raise InvalidCommit("Cannot create branch: repository has no commits yet")
        self.refs.create_branch(name, commit_oid)

    def list_branches(self) -> list[str]:
        return self.refs.list_branches()

    def delete_branch(self, name: str) -> None:
        current = self.refs.get_current_branch()
        if name == current:
            from .exceptions import MiniGitError
            raise MiniGitError(f"Cannot delete the currently checked-out branch '{name}'")
        self.refs.delete_branch(name)

    # ---------------------------------------------------------------
    # Repository-level stats (used by dashboard / API later)
    # ---------------------------------------------------------------
    def summary(self) -> dict:
        head_commit_oid = self.refs.get_head_commit()
        commits = self.log() if head_commit_oid else []
        latest_message = commits[0][1].message if commits else None
        return {
            "worktree": str(self.worktree),
            "branch": self.refs.get_current_branch(),
            "head": head_commit_oid,
            "commit_count": len(commits),
            "branch_count": len(self.list_branches()),
            "object_count": self.store.count(),
            "latest_message": latest_message,
        }
