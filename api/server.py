"""FastAPI application entry point.

This module contains NO version-control logic. Every route is a thin
adapter over core.repository.Repository -- the same class the CLI uses.
The one thing that lives here and only here is the mapping from
MiniGitError subclasses to HTTP status codes, so callers get structured,
predictable errors instead of a raw Python traceback or a generic 500.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.exceptions import (
    BranchAlreadyExists,
    BranchNotFound,
    InvalidCommit,
    InvalidObject,
    InvalidRepository,
    MergeConflict,
    MiniGitError,
    NothingToCommit,
    ObjectNotFound,
    PathspecError,
    RepositoryNotFound,
    UncommittedChanges,
)

from .routes import actions, branches, commits, objects, status

ERROR_STATUS_MAP = {
    RepositoryNotFound: 404,
    ObjectNotFound: 404,
    BranchNotFound: 404,
    InvalidObject: 422,
    InvalidCommit: 400,
    BranchAlreadyExists: 409,
    NothingToCommit: 400,
    UncommittedChanges: 409,
    InvalidRepository: 409,
    PathspecError: 400,
    MergeConflict: 409,
}

app = FastAPI(title="MiniGit API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(MiniGitError)
def handle_minigit_error(request: Request, exc: MiniGitError) -> JSONResponse:
    status_code = ERROR_STATUS_MAP.get(type(exc), 400)
    return JSONResponse(
        status_code=status_code,
        content={"error": type(exc).__name__, "message": str(exc)},
    )


app.include_router(status.router)
app.include_router(branches.router)
app.include_router(commits.router)
app.include_router(objects.router)
app.include_router(actions.router)
