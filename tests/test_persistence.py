"""Persistence tests: closing and reopening a Repository object simulates
a new process opening the same on-disk repository (e.g. CLI invoked twice)."""

from core.repository import Repository


def test_reopen_preserves_commit_history(tmp_path):
    repo1 = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("v1")
    repo1.add_path("a.txt")
    oid1 = repo1.commit("first")

    (tmp_path / "a.txt").write_text("v2")
    repo1.add_path("a.txt")
    oid2 = repo1.commit("second")

    # Simulate a fresh process: brand new Repository instance, same path.
    repo2 = Repository(tmp_path)
    entries = repo2.log()
    assert [oid for oid, _ in entries] == [oid2, oid1]


def test_reopen_preserves_branches(tmp_path):
    repo1 = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("v1")
    repo1.add_path("a.txt")
    repo1.commit("first")
    repo1.create_branch("feature")

    repo2 = Repository(tmp_path)
    assert set(repo2.list_branches()) == {"main", "feature"}


def test_reopen_preserves_index(tmp_path):
    repo1 = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("staged but not committed")
    repo1.add_path("a.txt")

    repo2 = Repository(tmp_path)
    assert "a.txt" in repo2.index.entries


def test_reopen_and_checkout_reconstructs_tree(tmp_path):
    from core.checkout import checkout_branch

    repo1 = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("v1")
    repo1.add_path("a.txt")
    repo1.commit("first")
    repo1.create_branch("feature")

    (tmp_path / "a.txt").write_text("v2")
    repo1.add_path("a.txt")
    repo1.commit("second")

    repo2 = Repository(tmp_path)
    checkout_branch(repo2, "feature")
    assert (tmp_path / "a.txt").read_text() == "v1"


def test_objects_survive_reopen_with_integrity(tmp_path):
    repo1 = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("content")
    repo1.add_path("a.txt")
    oid = repo1.commit("first")

    repo2 = Repository(tmp_path)
    commit = repo2.get_commit(oid)
    assert commit.message == "first"
