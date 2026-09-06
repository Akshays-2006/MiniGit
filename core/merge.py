"""Three-way merge between the current branch and another branch.

Steps:
    1. Find the merge base -- the lowest common ancestor of the two
       branch tips -- by BFS: collect every ancestor of the current
       commit, then walk the incoming commit's ancestry until we land on
       one of them.
    2. If the base IS the incoming commit, current already contains
       everything incoming has: nothing to do (already up to date).
    3. If the base IS the current commit, current hasn't diverged at all:
       fast-forward by just moving the branch pointer (no merge needed).
    4. Otherwise, real divergence: diff base->current and base->incoming
       per file. A file changed on only one side is taken from that side.
       A file changed identically on both sides is taken once. A file
       changed differently on both sides is passed to the line-level
       diff3 merge (core/diff3.py); if that still can't resolve every
       line, conflict markers are left in the file and it's reported as
       conflicted.
    5. A clean merge (no conflicts) is committed automatically with two
       parents. A conflicted merge stages everything that merged cleanly,
       writes conflict markers into the working tree for anything that
       didn't, and leaves the user to resolve + commit manually.
"""

from __future__ import annotations

import time

from .blob import Blob
from .checkout import checkout_branch
from .commit import Commit
from .diff3 import merge_lines
from .exceptions import BranchNotFound, MergeConflict, UncommittedChanges

DEFAULT_AUTHOR = "MiniGit User <user@example.com>"


def find_merge_base(repo, oid_a: str, oid_b: str) -> str:
    def ancestors_of(oid: str):
        seen = set()
        stack = [oid]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(repo.get_commit(cur).parents)
        return seen

    ancestors_a = ancestors_of(oid_a)
    if oid_b in ancestors_a:
        return oid_b

    seen = set()
    stack = [oid_b]
    while stack:
        cur = stack.pop()
        if cur in ancestors_a:
            return cur
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(repo.get_commit(cur).parents)

    raise MergeConflict("No common ancestor found -- branches share no history")


def merge_branch(repo, branch_name: str, author: str = DEFAULT_AUTHOR) -> dict:
    if not repo.refs.branch_exists(branch_name):
        raise BranchNotFound(f"Branch '{branch_name}' not found")
    if not repo.is_clean():
        raise UncommittedChanges("Commit or discard changes before merging")

    current_branch = repo.refs.get_current_branch()
    current_oid = repo.refs.get_head_commit()
    incoming_oid = repo.refs.get_branch_commit(branch_name)

    if current_oid is None:
        raise MergeConflict("Current branch has no commits to merge into")

    if current_oid == incoming_oid:
        return {"status": "already_up_to_date"}

    base_oid = find_merge_base(repo, current_oid, incoming_oid)

    if base_oid == incoming_oid:
        return {"status": "already_up_to_date"}

    if base_oid == current_oid:
        repo.refs.set_branch_commit(current_branch, incoming_oid)
        checkout_branch(repo, current_branch, force=True)
        return {"status": "fast_forward", "commit": incoming_oid}

    base_commit = repo.get_commit(base_oid)
    current_commit = repo.get_commit(current_oid)
    incoming_commit = repo.get_commit(incoming_oid)

    base_files = repo._flatten_tree(base_commit.tree)
    current_files = repo._flatten_tree(current_commit.tree)
    incoming_files = repo._flatten_tree(incoming_commit.tree)

    all_paths = set(base_files) | set(current_files) | set(incoming_files)
    clean_files: dict[str, bytes] = {}
    conflicted_files: list[str] = []

    for path in sorted(all_paths):
        base_f = base_files.get(path)
        current_f = current_files.get(path)
        incoming_f = incoming_files.get(path)

        if current_f == incoming_f:
            # Both sides agree -- including "both deleted" (None == None).
            if current_f is not None:
                clean_files[path] = repo.get_blob(current_f).content
            continue

        if current_f == base_f:
            # Untouched on current's side -- take whatever incoming did.
            if incoming_f is not None:
                clean_files[path] = repo.get_blob(incoming_f).content
            continue

        if incoming_f == base_f:
            # Untouched on incoming's side -- keep current.
            if current_f is not None:
                clean_files[path] = repo.get_blob(current_f).content
            continue

        # Both sides changed this path relative to base, and disagree.
        if current_f is None or incoming_f is None:
            # Modify/delete conflict: can't line-merge a deletion.
            conflicted_files.append(path)
            surviving_oid = current_f or incoming_f
            clean_files[path] = repo.get_blob(surviving_oid).content
            continue

        base_content = repo.get_blob(base_f).content if base_f else b""
        current_content = repo.get_blob(current_f).content
        incoming_content = repo.get_blob(incoming_f).content

        try:
            base_lines = base_content.decode().splitlines(keepends=True)
            current_lines = current_content.decode().splitlines(keepends=True)
            incoming_lines = incoming_content.decode().splitlines(keepends=True)
        except UnicodeDecodeError:
            conflicted_files.append(path)
            clean_files[path] = (
                b"<<<<<<< CURRENT (binary)\n" + current_content +
                b"\n=======\n" + incoming_content + b"\n>>>>>>> INCOMING (binary)\n"
            )
            continue

        merged_lines, has_conflict = merge_lines(base_lines, current_lines, incoming_lines)
        clean_files[path] = "".join(merged_lines).encode()
        if has_conflict:
            conflicted_files.append(path)

    # Write every merged file to the working tree.
    for path, content in clean_files.items():
        fpath = repo.worktree / path
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_bytes(content)

    for path in all_paths:
        if path not in clean_files:
            fpath = repo.worktree / path
            if fpath.exists():
                fpath.unlink()

    if conflicted_files:
        # Stage everything that merged cleanly; leave conflicted files
        # unstaged so `status` flags them until the user resolves + adds.
        for path, content in clean_files.items():
            if path in conflicted_files:
                continue
            oid = repo.store.write("blob", Blob(content).serialize())
            repo.index.add(path, oid)
        for path in list(repo.index.entries):
            if path not in clean_files:
                repo.index.remove(path)
        repo.index.save()
        return {"status": "conflict", "conflicted_files": sorted(conflicted_files)}

    for path, content in clean_files.items():
        oid = repo.store.write("blob", Blob(content).serialize())
        repo.index.add(path, oid)
    for path in list(repo.index.entries):
        if path not in clean_files:
            repo.index.remove(path)
    repo.index.save()

    tree_oid = repo._build_tree_from_index()
    commit_obj = Commit(
        tree=tree_oid,
        parents=[current_oid, incoming_oid],
        author=author,
        timestamp=time.time(),
        message=f"Merge branch '{branch_name}' into {current_branch}",
    )
    commit_oid = repo.store.write("commit", commit_obj.serialize())
    repo.refs.set_branch_commit(current_branch, commit_oid)

    return {
        "status": "merged",
        "commit": commit_oid,
        "merged_files": sorted(clean_files.keys()),
    }
