import pytest

from core.exceptions import NothingToCommit
from core.repository import Repository


def test_initial_commit(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("hello")
    repo.add_path("a.txt")
    oid = repo.commit("Initial commit")
    assert repo.refs.get_head_commit() == oid
    commit = repo.get_commit(oid)
    assert commit.parents == []
    assert commit.message == "Initial commit"


def test_commit_empty_index_raises(tmp_path):
    repo = Repository.init(tmp_path)
    with pytest.raises(NothingToCommit):
        repo.commit("nothing staged")


def test_commit_with_no_changes_raises(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("v1")
    repo.add_path("a.txt")
    repo.commit("first")
    # Re-stage identical content, tree hash will be unchanged.
    repo.add_path("a.txt")
    with pytest.raises(NothingToCommit):
        repo.commit("no-op")


def test_multiple_commits_form_chain(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("v1")
    repo.add_path("a.txt")
    oid1 = repo.commit("first")

    (tmp_path / "a.txt").write_text("v2")
    repo.add_path("a.txt")
    oid2 = repo.commit("second")

    commit2 = repo.get_commit(oid2)
    assert commit2.parents == [oid1]


def test_log_returns_all_ancestors(tmp_path):
    repo = Repository.init(tmp_path)
    for i in range(3):
        (tmp_path / "a.txt").write_text(f"v{i}")
        repo.add_path("a.txt")
        repo.commit(f"commit {i}")

    entries = repo.log()
    assert len(entries) == 3
    messages = [c.message for _, c in entries]
    # newest first
    assert messages == ["commit 2", "commit 1", "commit 0"]


def test_log_on_empty_repo_returns_empty(tmp_path):
    repo = Repository.init(tmp_path)
    assert repo.log() == []


def test_log_all_branches_unions_every_tip(tmp_path):
    from core.checkout import checkout_branch

    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("v0")
    repo.add_path("a.txt")
    repo.commit("base")
    repo.create_branch("feature")

    checkout_branch(repo, "feature")
    (tmp_path / "a.txt").write_text("v1-feature")
    repo.add_path("a.txt")
    repo.commit("feature-only commit")

    checkout_branch(repo, "main")
    (tmp_path / "a.txt").write_text("v1-main")
    repo.add_path("a.txt")
    repo.commit("main-only commit")

    all_entries = repo.log_all_branches()
    messages = {c.message for _, c in all_entries}
    assert messages == {"base", "feature-only commit", "main-only commit"}

    # HEAD-only log (currently on main) should NOT include feature's commit.
    head_only = {c.message for _, c in repo.log()}
    assert "feature-only commit" not in head_only


def test_tree_deduplication_across_commits(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("same")
    (tmp_path / "b.txt").write_text("changes")
    repo.add_path("a.txt")
    repo.add_path("b.txt")
    repo.commit("first")

    before_count = repo.store.count()

    # Only b.txt changes; a.txt's blob should be reused, not duplicated.
    (tmp_path / "b.txt").write_text("changed again")
    repo.add_path("b.txt")
    repo.commit("second")

    after_count = repo.store.count()
    # New objects: one new blob (b.txt v2), one new tree, one new commit = 3
    assert after_count - before_count == 3
