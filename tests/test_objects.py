import pytest

from core.exceptions import InvalidObject, ObjectNotFound
from core.objects import ObjectStore


def test_write_and_read_roundtrip(tmp_path):
    store = ObjectStore(tmp_path / "objects")
    oid = store.write("blob", b"hello world")
    obj_type, body = store.read(oid)
    assert obj_type == "blob"
    assert body == b"hello world"


def test_hash_is_deterministic(tmp_path):
    store = ObjectStore(tmp_path / "objects")
    oid1 = store.write("blob", b"same content")
    oid2 = store.write("blob", b"same content")
    assert oid1 == oid2


def test_identical_content_written_once(tmp_path):
    store = ObjectStore(tmp_path / "objects")
    store.write("blob", b"dedup me")
    store.write("blob", b"dedup me")
    assert store.count() == 1


def test_different_content_different_hash(tmp_path):
    store = ObjectStore(tmp_path / "objects")
    oid1 = store.write("blob", b"content A")
    oid2 = store.write("blob", b"content B")
    assert oid1 != oid2


def test_missing_object_raises(tmp_path):
    store = ObjectStore(tmp_path / "objects")
    with pytest.raises(ObjectNotFound):
        store.read("0" * 64)


def test_corrupted_object_detected(tmp_path):
    store = ObjectStore(tmp_path / "objects")
    oid = store.write("blob", b"original content")
    path = store._path_for(oid)
    path.write_bytes(b"blob 999\0tampered")
    with pytest.raises(InvalidObject):
        store.read(oid)


def test_exists(tmp_path):
    store = ObjectStore(tmp_path / "objects")
    oid = store.write("blob", b"x")
    assert store.exists(oid)
    assert not store.exists("f" * 64)
