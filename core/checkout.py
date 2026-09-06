"""Checkout: reconstruct the working tree from a branch's commit.

Kept as a standalone function (not a Repository method) because it's the
one operation that mutates the working tree wholesale, and isolating it
makes the "don't destroy uncommitted work" safety check easy to read and
test on its own.

Algorithm:
    1. Refuse if the working tree is dirty, unless `force=True`.
    2. Flatten the target commit's tree into {relpath: blob_oid}.
    3. Delete any currently-tracked file that doesn't exist in the target
       (handles files removed between branches).
    4. Write out every file in the target tree.
    5. Replace the index so it exactly mirrors the new HEAD (this keeps
       `status` clean immediately after a checkout).
    6. Repoint HEAD at the new branch.
"""

from __future__ import annotations

from .exceptions import BranchNotFound, UncommittedChanges


def checkout_branch(repo, branch_name: str, force: bool = False) -> str:
    if not repo.refs.branch_exists(branch_name):
        raise BranchNotFound(f"Branch '{branch_name}' not found")

    if not force and not repo.is_clean():
        raise UncommittedChanges(
            "You have uncommitted changes. Commit them, discard them, "
            "or re-run checkout with force=True."
        )

    target_commit_oid = repo.refs.get_branch_commit(branch_name)
    target_commit = repo.get_commit(target_commit_oid)
    target_files = repo._flatten_tree(target_commit.tree)

    currently_tracked = set(repo._get_head_tree_files().keys()) | set(repo.index.all_paths())
    for relpath in currently_tracked:
        if relpath not in target_files:
            fpath = repo.worktree / relpath
            if fpath.exists():
                fpath.unlink()

    for relpath, blob_oid in target_files.items():
        blob = repo.get_blob(blob_oid)
        fpath = repo.worktree / relpath
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_bytes(blob.content)

    repo.index.entries = {p: {"hash": h, "mode": "100644"} for p, h in target_files.items()}
    repo.index.save()

    repo.refs.set_head_ref(f"refs/heads/{branch_name}")
    return target_commit_oid
