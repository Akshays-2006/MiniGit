import pytest

from core.checkout import checkout_branch
from core.exceptions import BranchNotFound, UncommittedChanges
from core.merge import merge_branch
from core.repository import Repository


def _base_repo(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "shared.txt").write_text("line1\nline2\nline3\n")
    repo.add_path("shared.txt")
    repo.commit("base commit")
    repo.create_branch("feature")
    return repo


def test_merge_unknown_branch_raises(tmp_path):
    repo = _base_repo(tmp_path)
    with pytest.raises(BranchNotFound):
        merge_branch(repo, "does-not-exist")


def test_merge_refuses_with_uncommitted_changes(tmp_path):
    repo = _base_repo(tmp_path)
    (tmp_path / "shared.txt").write_text("dirty")
    with pytest.raises(UncommittedChanges):
        merge_branch(repo, "feature")


def test_merge_already_up_to_date(tmp_path):
    repo = _base_repo(tmp_path)
    result = merge_branch(repo, "feature")
    assert result["status"] == "already_up_to_date"


def test_fast_forward_merge(tmp_path):
    repo = _base_repo(tmp_path)
    checkout_branch(repo, "feature")
    (tmp_path / "shared.txt").write_text("line1\nline2\nline3\nline4\n")
    repo.add_path("shared.txt")
    repo.commit("feature advances")

    checkout_branch(repo, "main")
    result = merge_branch(repo, "feature")
    assert result["status"] == "fast_forward"
    assert (tmp_path / "shared.txt").read_text() == "line1\nline2\nline3\nline4\n"


def test_clean_three_way_merge_non_overlapping_changes(tmp_path):
    repo = _base_repo(tmp_path)

    checkout_branch(repo, "feature")
    (tmp_path / "shared.txt").write_text("line1\nline2\nline3-changed-on-feature\n")
    repo.add_path("shared.txt")
    repo.commit("feature edits line3")

    checkout_branch(repo, "main")
    (tmp_path / "shared.txt").write_text("line1-changed-on-main\nline2\nline3\n")
    repo.add_path("shared.txt")
    repo.commit("main edits line1")

    result = merge_branch(repo, "feature")
    assert result["status"] == "merged"
    content = (tmp_path / "shared.txt").read_text()
    assert "line1-changed-on-main" in content
    assert "line3-changed-on-feature" in content
    assert "<<<<<<<" not in content

    # Merge commit should have two parents.
    head = repo.refs.get_head_commit()
    commit = repo.get_commit(head)
    assert len(commit.parents) == 2


def test_merge_creates_new_file_from_incoming(tmp_path):
    repo = _base_repo(tmp_path)
    checkout_branch(repo, "feature")
    (tmp_path / "only_on_feature.txt").write_text("hello")
    repo.add_path("only_on_feature.txt")
    repo.commit("add new file")

    # Give main its own independent commit so this is a genuine 3-way
    # merge rather than a fast-forward.
    checkout_branch(repo, "main")
    (tmp_path / "main_only.txt").write_text("main work")
    repo.add_path("main_only.txt")
    repo.commit("main advances independently")

    result = merge_branch(repo, "feature")
    assert result["status"] == "merged"
    assert (tmp_path / "only_on_feature.txt").read_text() == "hello"
    assert (tmp_path / "main_only.txt").read_text() == "main work"


def test_conflicting_merge_reports_conflict_and_writes_markers(tmp_path):
    repo = _base_repo(tmp_path)

    checkout_branch(repo, "feature")
    (tmp_path / "shared.txt").write_text("line1\nFEATURE_VERSION\nline3\n")
    repo.add_path("shared.txt")
    repo.commit("feature changes line2")

    checkout_branch(repo, "main")
    (tmp_path / "shared.txt").write_text("line1\nMAIN_VERSION\nline3\n")
    repo.add_path("shared.txt")
    repo.commit("main changes line2")

    result = merge_branch(repo, "feature")
    assert result["status"] == "conflict"
    assert "shared.txt" in result["conflicted_files"]

    content = (tmp_path / "shared.txt").read_text()
    assert "<<<<<<< CURRENT" in content
    assert "MAIN_VERSION" in content
    assert "FEATURE_VERSION" in content
    assert ">>>>>>> INCOMING" in content

    # Conflicted file should show up as unresolved in status.
    status = repo.status()
    assert "shared.txt" not in status["staged"]


def test_resolve_conflict_and_commit(tmp_path):
    repo = _base_repo(tmp_path)

    checkout_branch(repo, "feature")
    (tmp_path / "shared.txt").write_text("line1\nFEATURE_VERSION\nline3\n")
    repo.add_path("shared.txt")
    repo.commit("feature changes line2")

    checkout_branch(repo, "main")
    (tmp_path / "shared.txt").write_text("line1\nMAIN_VERSION\nline3\n")
    repo.add_path("shared.txt")
    repo.commit("main changes line2")

    merge_branch(repo, "feature")

    # Manually resolve the conflict.
    (tmp_path / "shared.txt").write_text("line1\nRESOLVED\nline3\n")
    repo.add_path("shared.txt")
    oid = repo.commit("resolve merge conflict")
    assert repo.get_commit(oid).message == "resolve merge conflict"
    assert repo.is_clean()
