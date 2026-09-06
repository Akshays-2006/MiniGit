"""Repository resolution for API requests.

The API is a thin adapter: every route resolves a Repository the same
way the CLI does (Repository.find), then calls the exact same core
methods the CLI calls. No business logic lives in routes/.

Repo location resolution order:
    1. `?repo_path=` query param, if the client passes one (lets the
       frontend point at an arbitrary repo on disk).
    2. MINIGIT_REPO_PATH environment variable.
    3. Current working directory of the API process.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import Query

from core.repository import Repository


def get_repo(repo_path: str | None = Query(default=None)) -> Repository:
    start = repo_path or os.environ.get("MINIGIT_REPO_PATH") or "."
    return Repository.find(Path(start))
