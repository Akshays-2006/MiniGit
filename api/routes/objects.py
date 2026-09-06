from fastapi import APIRouter, Depends

from core.repository import Repository

from ..deps import get_repo

router = APIRouter(tags=["objects"])


def _entries_payload(tree):
    return [
        {"name": e.name, "hash": e.hash, "type": e.type, "mode": e.mode}
        for e in sorted(tree.entries, key=lambda e: e.name)
    ]


@router.get("/api/objects/{hash}")
def inspect_object(hash: str, repo: Repository = Depends(get_repo)):
    obj_type, _ = repo.store.read(hash)
    if obj_type == "commit":
        c = repo.get_commit(hash)
        return {
            "type": "commit", "hash": hash, "tree": c.tree, "parents": c.parents,
            "author": c.author, "timestamp": c.timestamp, "message": c.message,
        }
    if obj_type == "tree":
        t = repo.get_tree(hash)
        return {"type": "tree", "hash": hash, "entries": _entries_payload(t)}
    b = repo.get_blob(hash)
    try:
        content, binary = b.content.decode(), False
    except UnicodeDecodeError:
        content, binary = None, True
    return {
        "type": "blob",
        "hash": hash,
        "size": len(b.content),
        "binary": binary,
        "content": content,
    }


@router.get("/api/tree/{hash}")
def get_tree(hash: str, repo: Repository = Depends(get_repo)):
    t = repo.get_tree(hash)
    return {"hash": hash, "entries": _entries_payload(t)}
