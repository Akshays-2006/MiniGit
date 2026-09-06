"""Diff: compare two flat file-maps (tree snapshots or the working tree)
and report added/deleted/modified files, with line-level hunks for
modified files.

Kept as functions (not a Repository method) operating on the
{relpath: blob_oid} maps that Repository._flatten_tree already produces,
so the same code diffs commit-vs-commit, HEAD-vs-working-tree, or
base-vs-current-vs-incoming (reused by merge.py).
"""

from __future__ import annotations

import difflib


def _line_diff(old_content: bytes, new_content: bytes, path: str) -> list[str]:
    try:
        old_lines = old_content.decode().splitlines(keepends=True)
        new_lines = new_content.decode().splitlines(keepends=True)
    except UnicodeDecodeError:
        return ["<binary file differs>\n"]
    return list(
        difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{path}", tofile=f"b/{path}")
    )


def diff_flat_trees(repo, old_files: dict[str, str], new_files: dict[str, str]) -> dict:
    old_paths = set(old_files)
    new_paths = set(new_files)
    added = sorted(new_paths - old_paths)
    deleted = sorted(old_paths - new_paths)
    modified = []
    for path in sorted(old_paths & new_paths):
        if old_files[path] != new_files[path]:
            old_content = repo.get_blob(old_files[path]).content
            new_content = repo.get_blob(new_files[path]).content
            modified.append({"path": path, "hunks": _line_diff(old_content, new_content, path)})
    return {"added": added, "deleted": deleted, "modified": modified}


def diff_commit_to_commit(repo, old_commit_oid: str, new_commit_oid: str) -> dict:
    old_commit = repo.get_commit(old_commit_oid)
    new_commit = repo.get_commit(new_commit_oid)
    old_files = repo._flatten_tree(old_commit.tree)
    new_files = repo._flatten_tree(new_commit.tree)
    return diff_flat_trees(repo, old_files, new_files)


def diff_working_tree(repo) -> dict:
    """Diff HEAD's tree against the current working tree's actual contents
    (not the index -- this shows unstaged changes plus untracked/deleted
    files, the same universe `status()` reports on)."""
    head_files = repo._get_head_tree_files()
    working_paths = set(repo._iter_worktree_files())

    added = sorted(working_paths - set(head_files))
    deleted = sorted(set(head_files) - working_paths)
    modified = []
    for path in sorted(working_paths & set(head_files)):
        content = repo._read_worktree_file(path)
        current_hash = repo.store.hash_bytes(f"blob {len(content)}\0".encode() + content)
        if current_hash != head_files[path]:
            old_content = repo.get_blob(head_files[path]).content
            modified.append({"path": path, "hunks": _line_diff(old_content, content, path)})
    return {"added": added, "deleted": deleted, "modified": modified}
