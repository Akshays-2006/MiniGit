from fastapi import APIRouter, Depends

from core.repository import Repository

from ..deps import get_repo
from ..schemas import BranchCreateRequest

router = APIRouter(tags=["branches"])


@router.get("/api/branches")
def list_branches(repo: Repository = Depends(get_repo)):
    return {
        "current": repo.refs.get_current_branch(),
        "branches": [
            {"name": name, "commit": repo.refs.get_branch_commit(name)}
            for name in repo.list_branches()
        ],
    }


@router.post("/api/branches", status_code=201)
def create_branch(payload: BranchCreateRequest, repo: Repository = Depends(get_repo)):
    repo.create_branch(payload.name, start_commit=payload.start_commit)
    return {"name": payload.name, "commit": repo.refs.get_branch_commit(payload.name)}
