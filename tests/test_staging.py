import pytest

from core.exceptions import InvalidRepository, PathspecError, RepositoryNotFound
from core.repository import Repository


def test_init_creates_structure(tmp_path):
    repo = Repository.init(tmp_path)
    assert (repo.minigit_dir / "objects").is_dir()
    assert (repo.minigit_dir / "refs" / "heads").is_dir()
    assert (repo.minigit_dir / "HEAD").exists()
    assert repo.refs.get_current_branch() == "main"


def test_init_twice_raises(tmp_path):
    Repository.init(tmp_path)
    with pytest.raises(InvalidRepository):
        Repository.init(tmp_path)


def test_find_walks_up_parents(tmp_path):
    Repository.init(tmp_path)
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    repo = Repository.find(nested)
    assert repo.worktree == tmp_path.resolve()


def test_find_raises_outside_repo(tmp_path):
    with pytest.raises(RepositoryNotFound):
        Repository.find(tmp_path)


def test_add_single_file(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "hello.txt").write_text("hello")
    staged = repo.add_path("hello.txt")
    assert staged == ["hello.txt"]
    assert "hello.txt" in repo.index.entries


def test_add_directory_stages_all_files(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("a")
    (tmp_path / "src" / "b.py").write_text("b")
    staged = repo.add_path("src")
    assert set(staged) == {"src/a.py", "src/b.py"}


def test_add_missing_path_raises(tmp_path):
    repo = Repository.init(tmp_path)
    with pytest.raises(PathspecError):
        repo.add_path("does_not_exist.txt")


def test_status_untracked(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "new.txt").write_text("new")
    status = repo.status()
    assert status["untracked"] == ["new.txt"]
    assert status["staged"] == []


def test_status_staged(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("content")
    repo.add_path("a.txt")
    status = repo.status()
    assert status["staged"] == ["a.txt"]
    assert status["untracked"] == []


def test_status_modified_after_commit(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("v1")
    repo.add_path("a.txt")
    repo.commit("first")

    (tmp_path / "a.txt").write_text("v2")
    status = repo.status()
    assert status["modified_unstaged"] == ["a.txt"]


def test_status_deleted_file(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("v1")
    repo.add_path("a.txt")
    repo.commit("first")

    (tmp_path / "a.txt").unlink()
    status = repo.status()
    assert status["deleted"] == ["a.txt"]


def test_status_clean_after_commit(tmp_path):
    repo = Repository.init(tmp_path)
    (tmp_path / "a.txt").write_text("v1")
    repo.add_path("a.txt")
    repo.commit("first")
    assert repo.is_clean()
