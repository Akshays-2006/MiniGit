from core.blob import Blob
from core.commit import Commit
from core.tree import Tree, TreeEntry


def test_blob_roundtrip():
    b = Blob(content=b"print('hi')")
    body = b.serialize()
    b2 = Blob.deserialize(body)
    assert b2.content == b"print('hi')"


def test_tree_roundtrip_and_sorting():
    entries = [
        TreeEntry(mode="100644", type="blob", hash="b" * 64, name="zeta.py"),
        TreeEntry(mode="100644", type="blob", hash="a" * 64, name="alpha.py"),
    ]
    tree = Tree(entries=entries)
    body = tree.serialize()
    lines = body.decode().splitlines()
    assert lines[0].endswith("alpha.py")
    assert lines[1].endswith("zeta.py")

    tree2 = Tree.deserialize(body)
    names = sorted(e.name for e in tree2.entries)
    assert names == ["alpha.py", "zeta.py"]


def test_tree_hash_independent_of_insertion_order():
    from core.objects import ObjectStore
    e1 = TreeEntry(mode="100644", type="blob", hash="a" * 64, name="a.py")
    e2 = TreeEntry(mode="100644", type="blob", hash="b" * 64, name="b.py")

    body1 = Tree(entries=[e1, e2]).serialize()
    body2 = Tree(entries=[e2, e1]).serialize()
    assert body1 == body2
    assert ObjectStore.hash_bytes(body1) == ObjectStore.hash_bytes(body2)


def test_commit_roundtrip_single_parent():
    c = Commit(
        tree="t" * 64,
        parents=["p" * 64],
        author="Akshay <a@example.com>",
        timestamp=1234.5,
        message="Initial commit",
    )
    body = c.serialize()
    c2 = Commit.deserialize(body)
    assert c2.tree == c.tree
    assert c2.parents == c.parents
    assert c2.author == c.author
    assert c2.timestamp == c.timestamp
    assert c2.message == c.message


def test_commit_roundtrip_merge_multi_parent():
    c = Commit(
        tree="t" * 64,
        parents=["p1" + "1" * 62, "p2" + "2" * 62],
        author="Akshay <a@example.com>",
        timestamp=999.0,
        message="Merge branch 'feature'",
    )
    body = c.serialize()
    c2 = Commit.deserialize(body)
    assert c2.parents == c.parents


def test_commit_roundtrip_multiline_message():
    c = Commit(
        tree="t" * 64,
        parents=[],
        author="Akshay <a@example.com>",
        timestamp=1.0,
        message="Title line\n\nBody paragraph with detail.",
    )
    body = c.serialize()
    c2 = Commit.deserialize(body)
    assert c2.message == c.message
