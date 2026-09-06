from fastapi import APIRouter, Depends

from core.diff import diff_commit_to_commit, diff_flat_trees
from core.repository import Repository

from ..deps import get_repo

router = APIRouter(tags=["commits"])


def _serialize_commit(oid: str, commit) -> dict:
    return {
        "hash": oid,
        "short_hash": oid[:7],
        "tree": commit.tree,
        "parents": commit.parents,
        "author": commit.author,
        "timestamp": commit.timestamp,
        "message": commit.message,
    }


@router.get("/api/commits")
def list_commits(all: bool = True, repo: Repository = Depends(get_repo)):
    entries = repo.log_all_branches() if all else repo.log()
    return [_serialize_commit(oid, c) for oid, c in entries]


@router.get("/api/commits/{hash}")
def get_commit(hash: str, repo: Repository = Depends(get_repo)):
    commit = repo.get_commit(hash)
    return _serialize_commit(hash, commit)


@router.get("/api/commits/{hash}/diff")
def get_commit_diff(hash: str, repo: Repository = Depends(get_repo)):
    commit = repo.get_commit(hash)
    if commit.parents:
        return diff_commit_to_commit(repo, commit.parents[0], hash)
    # Root commit: everything in its tree is "added" relative to nothing.
    new_files = repo._flatten_tree(commit.tree)
    return diff_flat_trees(repo, {}, new_files)
