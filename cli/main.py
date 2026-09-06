"""MiniGit command-line interface.

Deliberately thin: every command parses args, calls into Repository /
checkout, and formats the result. No git logic lives here -- this same
Repository class is what the REST API (Phase 2) will call too.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.checkout import checkout_branch
from core.diff import diff_commit_to_commit, diff_working_tree
from core.exceptions import MiniGitError
from core.merge import merge_branch
from core.repository import Repository


def cmd_init(args):
    repo = Repository.init(Path(args.path))
    print(f"Initialized empty MiniGit repository in {repo.minigit_dir}")


def cmd_add(args):
    repo = Repository.find()
    staged = repo.add_path(args.path)
    for relpath in staged:
        print(f"add '{relpath}'")


def cmd_status(args):
    repo = Repository.find()
    status = repo.status()
    print(f"On branch {status['branch']}")
    if status["staged"]:
        print("\nChanges to be committed:")
        for f in status["staged"]:
            print(f"  staged:   {f}")
    if status["modified_unstaged"]:
        print("\nChanges not staged for commit:")
        for f in status["modified_unstaged"]:
            print(f"  modified: {f}")
    if status["deleted"]:
        print("\nDeleted files:")
        for f in status["deleted"]:
            print(f"  deleted:  {f}")
    if status["untracked"]:
        print("\nUntracked files:")
        for f in status["untracked"]:
            print(f"  {f}")
    if not any(status[k] for k in ("staged", "modified_unstaged", "deleted", "untracked")):
        print("\nnothing to commit, working tree clean")


def cmd_commit(args):
    repo = Repository.find()
    oid = repo.commit(args.message)
    short = oid[:7]
    branch = repo.refs.get_current_branch()
    print(f"[{branch} {short}] {args.message}")


def cmd_log(args):
    repo = Repository.find()
    entries = repo.log()
    if not entries:
        print("No commits yet")
        return
    for oid, commit in entries:
        print(f"{oid[:7]}  {commit.message}")
        if args.verbose:
            print(f"  hash:    {oid}")
            print(f"  author:  {commit.author}")
            print(f"  parents: {', '.join(p[:7] for p in commit.parents) or '(none)'}")


def cmd_branch(args):
    repo = Repository.find()
    if args.name:
        repo.create_branch(args.name)
        print(f"Created branch '{args.name}'")
    else:
        current = repo.refs.get_current_branch()
        for b in repo.list_branches():
            marker = "* " if b == current else "  "
            print(f"{marker}{b}")


def cmd_checkout(args):
    repo = Repository.find()
    checkout_branch(repo, args.branch, force=args.force)
    print(f"Switched to branch '{args.branch}'")


def cmd_inspect(args):
    repo = Repository.find()
    obj_type, body = repo.store.read(args.hash)
    print(f"type: {obj_type}")
    print(f"hash: {args.hash}")
    if obj_type == "commit":
        c = repo.get_commit(args.hash)
        print(f"tree: {c.tree}")
        for p in c.parents:
            print(f"parent: {p}")
        print(f"author: {c.author}")
        print(f"timestamp: {c.timestamp}")
        print(f"message: {c.message}")
    elif obj_type == "tree":
        t = repo.get_tree(args.hash)
        print("entries:")
        for e in sorted(t.entries, key=lambda e: e.name):
            print(f"  {e.name} -> {e.hash} ({e.type})")
    elif obj_type == "blob":
        b = repo.get_blob(args.hash)
        print(f"size: {len(b.content)}")
        try:
            print(f"content:\n{b.content.decode()}")
        except UnicodeDecodeError:
            print("content: <binary>")


def _print_diff_result(result):
    for path in result["added"]:
        print(f"added:    {path}")
    for path in result["deleted"]:
        print(f"deleted:  {path}")
    for entry in result["modified"]:
        print(f"modified: {entry['path']}")
        for line in entry["hunks"]:
            print(line, end="" if line.endswith("\n") else "\n")
    if not (result["added"] or result["deleted"] or result["modified"]):
        print("no differences")


def cmd_diff(args):
    repo = Repository.find()
    if args.commit:
        head_oid = repo.refs.get_head_commit()
        result = diff_commit_to_commit(repo, args.commit, head_oid)
    else:
        result = diff_working_tree(repo)
    _print_diff_result(result)


def cmd_merge(args):
    repo = Repository.find()
    result = merge_branch(repo, args.branch)
    status = result["status"]
    if status == "already_up_to_date":
        print("Already up to date.")
    elif status == "fast_forward":
        print(f"Fast-forward merge to {result['commit'][:7]}")
    elif status == "merged":
        print(f"Merge commit created: {result['commit'][:7]}")
        for f in result["merged_files"]:
            print(f"  merged: {f}")
    elif status == "conflict":
        print("Automatic merge failed; fix conflicts and then commit the result:")
        for f in result["conflicted_files"]:
            print(f"  both modified: {f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="minigit")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="initialize a new repository")
    p_init.add_argument("path", nargs="?", default=".")
    p_init.set_defaults(func=cmd_init)

    p_add = sub.add_parser("add", help="stage a file or directory")
    p_add.add_argument("path")
    p_add.set_defaults(func=cmd_add)

    p_status = sub.add_parser("status", help="show working tree status")
    p_status.set_defaults(func=cmd_status)

    p_commit = sub.add_parser("commit", help="record staged changes")
    p_commit.add_argument("message")
    p_commit.set_defaults(func=cmd_commit)

    p_log = sub.add_parser("log", help="show commit history")
    p_log.add_argument("-v", "--verbose", action="store_true")
    p_log.set_defaults(func=cmd_log)

    p_branch = sub.add_parser("branch", help="list or create branches")
    p_branch.add_argument("name", nargs="?", default=None)
    p_branch.set_defaults(func=cmd_branch)

    p_checkout = sub.add_parser("checkout", help="switch branches")
    p_checkout.add_argument("branch")
    p_checkout.add_argument("--force", action="store_true")
    p_checkout.set_defaults(func=cmd_checkout)

    p_inspect = sub.add_parser("inspect", help="inspect a raw object")
    p_inspect.add_argument("hash")
    p_inspect.set_defaults(func=cmd_inspect)

    p_diff = sub.add_parser("diff", help="show changes")
    p_diff.add_argument("commit", nargs="?", default=None, help="diff this commit against HEAD")
    p_diff.set_defaults(func=cmd_diff)

    p_merge = sub.add_parser("merge", help="merge a branch into the current branch")
    p_merge.add_argument("branch")
    p_merge.set_defaults(func=cmd_merge)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except MiniGitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
