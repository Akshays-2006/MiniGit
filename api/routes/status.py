from fastapi import APIRouter, Depends

from core.repository import Repository

from ..deps import get_repo

router = APIRouter(tags=["status"])


@router.get("/api/status")
def get_status(repo: Repository = Depends(get_repo)):
    return repo.status()


@router.get("/api/summary")
def get_summary(repo: Repository = Depends(get_repo)):
    """Extra endpoint (not in the original spec) backing the dashboard
    overview screen: branch/HEAD/commit-count/object-count in one call."""
    return repo.summary()
