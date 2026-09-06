import pytest

from core.checkout import checkout_branch
from core.exceptions import BranchAlreadyExists, BranchNotFound, InvalidCommit, UncommittedChanges
from core.repository import Repository


def _init_with_commit(tmp_path, filename="a.txt", content="v1", message="first"):
    repo = Repository.init(tmp_path)
    (tmp_path / filename).write_text(content)
    repo.add_path(filename)
    repo.commit(message)
    return repo


def test_create_branch(tmp_path):
    repo = _init_with_commit(tmp_path)
    repo.create_branch("feature")
    assert "feature" in repo.list_branches()


def test_create_branch_without_commits_raises(tmp_path):
    repo = Repository.init(tmp_path)
    with pytest.raises(InvalidCommit):
        repo.create_branch("feature")


def test_create_duplicate_branch_raises(tmp_path):
    repo = _init_with_commit(tmp_path)
    repo.create_branch("feature")
    with pytest.raises(BranchAlreadyExists):
        repo.create_branch("feature")


def test_checkout_switches_branch(tmp_path):
    repo = _init_with_commit(tmp_path)
    repo.create_branch("feature")
    checkout_branch(repo, "feature")
    assert repo.refs.get_current_branch() == "feature"


def test_checkout_unknown_branch_raises(tmp_path):
    repo = _init_with_commit(tmp_path)
    with pytest.raises(BranchNotFound):
        checkout_branch(repo, "does-not-exist")


def test_checkout_reconstructs_working_tree(tmp_path):
    repo = _init_with_commit(tmp_path, content="v1")
    repo.create_branch("feature")
    checkout_branch(repo, "feature")

    (tmp_path / "a.txt").write_text("v2-on-feature")
    repo.add_path("a.txt")
    repo.commit("second on feature")

    checkout_branch(repo, "main")
    assert (tmp_path / "a.txt").read_text() == "v1"

    checkout_branch(repo, "feature")
    assert (tmp_path / "a.txt").read_text() == "v2-on-feature"


def test_checkout_refuses_with_uncommitted_changes(tmp_path):
    repo = _init_with_commit(tmp_path)
    repo.create_branch("feature")
    (tmp_path / "a.txt").write_text("dirty change")
    with pytest.raises(UncommittedChanges):
        checkout_branch(repo, "feature")


def test_checkout_force_overrides_dirty_check(tmp_path):
    repo = _init_with_commit(tmp_path)
    repo.create_branch("feature")
    (tmp_path / "a.txt").write_text("dirty change")
    checkout_branch(repo, "feature", force=True)
    assert repo.refs.get_current_branch() == "feature"


def test_create_branch_with_slash_in_name(tmp_path):
    repo = _init_with_commit(tmp_path)
    repo.create_branch("feature/auth")
    assert "feature/auth" in repo.list_branches()
    checkout_branch(repo, "feature/auth")
    assert repo.refs.get_current_branch() == "feature/auth"


def test_branch_independence(tmp_path):
    repo = _init_with_commit(tmp_path)
    repo.create_branch("feature")
    checkout_branch(repo, "feature")

    (tmp_path / "new_on_feature.txt").write_text("only on feature")
    repo.add_path("new_on_feature.txt")
    repo.commit("feature-only commit")

    checkout_branch(repo, "main")
    assert not (tmp_path / "new_on_feature.txt").exists()

    main_log = repo.log()
    assert len(main_log) == 1  # feature's extra commit doesn't show up on main


def test_checkout_removes_file_deleted_on_target_branch(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "keep.txt").write_text("keep")
    (tmp_path / "remove.txt").write_text("remove me")
    repo.add_path("keep.txt")
    repo.add_path("remove.txt")
    repo.commit("first")
    repo.create_branch("feature")

    checkout_branch(repo, "feature")
    (tmp_path / "remove.txt").unlink()
    repo.index.remove("remove.txt")
    repo.index.save()
    repo.commit("remove file on feature")

    checkout_branch(repo, "main")
    assert (tmp_path / "remove.txt").exists()

    checkout_branch(repo, "feature")
    assert not (tmp_path / "remove.txt").exists()
