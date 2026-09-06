
import pytest
from fastapi.testclient import TestClient

from core.repository import Repository


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("hello")
    repo.add_path("a.txt")
    repo.commit("initial commit")

    monkeypatch.setenv("MINIGIT_REPO_PATH", str(tmp_path))
    from api.server import app
    return TestClient(app), repo, tmp_path


def test_get_status(api_client):
    client, repo, _ = api_client
    resp = client.get("/api/status")
    assert resp.status_code == 200
    assert resp.json()["branch"] == "main"


def test_get_branches(api_client):
    client, repo, _ = api_client
    resp = client.get("/api/branches")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current"] == "main"
    assert any(b["name"] == "main" for b in data["branches"])


def test_create_branch(api_client):
    client, repo, _ = api_client
    resp = client.post("/api/branches", json={"name": "feature"})
    assert resp.status_code == 201
    assert "feature" in repo.list_branches()


def test_create_duplicate_branch_returns_409(api_client):
    client, repo, _ = api_client
    client.post("/api/branches", json={"name": "feature"})
    resp = client.post("/api/branches", json={"name": "feature"})
    assert resp.status_code == 409
    assert resp.json()["error"] == "BranchAlreadyExists"


def test_list_commits(api_client):
    client, repo, _ = api_client
    resp = client.get("/api/commits")
    assert resp.status_code == 200
    commits = resp.json()
    assert len(commits) == 1
    assert commits[0]["message"] == "initial commit"


def test_get_commit_by_hash(api_client):
    client, repo, _ = api_client
    head = repo.refs.get_head_commit()
    resp = client.get(f"/api/commits/{head}")
    assert resp.status_code == 200
    assert resp.json()["hash"] == head


def test_get_commit_not_found_returns_404(api_client):
    client, repo, _ = api_client
    resp = client.get(f"/api/commits/{'0'*64}")
    assert resp.status_code == 404
    assert resp.json()["error"] == "ObjectNotFound"


def test_get_commit_diff_root_commit(api_client):
    client, repo, _ = api_client
    head = repo.refs.get_head_commit()
    resp = client.get(f"/api/commits/{head}/diff")
    assert resp.status_code == 200
    data = resp.json()
    assert "a.txt" in data["added"]


def test_get_object_inspect_blob(api_client):
    client, repo, tmp_path = api_client
    head = repo.refs.get_head_commit()
    commit = repo.get_commit(head)
    tree = repo.get_tree(commit.tree)
    blob_oid = next(e.hash for e in tree.entries if e.name == "a.txt")

    resp = client.get(f"/api/objects/{blob_oid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "blob"
    assert data["content"] == "hello"


def test_checkout_via_api(api_client):
    client, repo, _ = api_client
    repo.create_branch("feature")
    resp = client.post("/api/checkout", json={"branch": "feature"})
    assert resp.status_code == 200
    assert repo.refs.get_current_branch() == "feature"


def test_checkout_unknown_branch_returns_404(api_client):
    client, repo, _ = api_client
    resp = client.post("/api/checkout", json={"branch": "nope"})
    assert resp.status_code == 404
    assert resp.json()["error"] == "BranchNotFound"


def test_merge_via_api(api_client):
    client, repo, tmp_path = api_client
    repo.create_branch("feature")
    from core.checkout import checkout_branch
    checkout_branch(repo, "feature")
    (tmp_path / "a.txt").write_text("hello v2")
    repo.add_path("a.txt")
    repo.commit("feature edit")
    checkout_branch(repo, "main")

    resp = client.post("/api/merge", json={"branch": "feature"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "fast_forward"


def test_get_summary(api_client):
    client, repo, _ = api_client
    resp = client.get("/api/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["commit_count"] == 1
    assert data["branch"] == "main"
