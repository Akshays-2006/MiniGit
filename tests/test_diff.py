from core.diff import diff_commit_to_commit, diff_working_tree
from core.repository import Repository


def test_diff_working_tree_detects_added_file(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("v1")
    repo.add_path("a.txt")
    repo.commit("first")

    (tmp_path / "new.txt").write_text("new content")
    result = diff_working_tree(repo)
    assert result["added"] == ["new.txt"]
    assert result["modified"] == []
    assert result["deleted"] == []


def test_diff_working_tree_detects_modified_file(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("line1\nline2\n")
    repo.add_path("a.txt")
    repo.commit("first")

    (tmp_path / "a.txt").write_text("line1\nCHANGED\n")
    result = diff_working_tree(repo)
    assert len(result["modified"]) == 1
    assert result["modified"][0]["path"] == "a.txt"
    hunk_text = "".join(result["modified"][0]["hunks"])
    assert "-line2" in hunk_text
    assert "+CHANGED" in hunk_text


def test_diff_working_tree_detects_deleted_file(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("content")
    repo.add_path("a.txt")
    repo.commit("first")

    (tmp_path / "a.txt").unlink()
    result = diff_working_tree(repo)
    assert result["deleted"] == ["a.txt"]


def test_diff_commit_to_commit(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("v1")
    repo.add_path("a.txt")
    oid1 = repo.commit("first")

    (tmp_path / "a.txt").write_text("v2")
    repo.add_path("a.txt")
    oid2 = repo.commit("second")

    result = diff_commit_to_commit(repo, oid1, oid2)
    assert len(result["modified"]) == 1
    assert result["modified"][0]["path"] == "a.txt"


def test_diff_no_changes(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("stable")
    repo.add_path("a.txt")
    repo.commit("first")
    result = diff_working_tree(repo)
    assert result == {"added": [], "deleted": [], "modified": []}
