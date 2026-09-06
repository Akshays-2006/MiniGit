
from pydantic import BaseModel


class BranchCreateRequest(BaseModel):
    name: str
    start_commit: str | None = None


class CheckoutRequest(BaseModel):
    branch: str
    force: bool = False


class MergeRequest(BaseModel):
    branch: str
