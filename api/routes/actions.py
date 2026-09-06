from fastapi import APIRouter, Depends

from core.checkout import checkout_branch
from core.merge import merge_branch
from core.repository import Repository

from ..deps import get_repo
from ..schemas import CheckoutRequest, MergeRequest

router = APIRouter(tags=["actions"])


@router.post("/api/checkout")
def checkout(payload: CheckoutRequest, repo: Repository = Depends(get_repo)):
    checkout_branch(repo, payload.branch, force=payload.force)
    return {"branch": payload.branch, "head": repo.refs.get_head_commit()}


@router.post("/api/merge")
def merge(payload: MergeRequest, repo: Repository = Depends(get_repo)):
    return merge_branch(repo, payload.branch)
