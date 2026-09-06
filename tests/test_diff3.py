from core.diff3 import merge_lines


def _lines(text):
    return text.splitlines(keepends=True)


def test_no_changes_either_side():
    base = _lines("a\nb\nc\n")
    merged, conflict = merge_lines(base, base, base)
    assert merged == base
    assert not conflict


def test_only_current_changed():
    base = _lines("a\nb\nc\n")
    current = _lines("a\nB\nc\n")
    incoming = _lines("a\nb\nc\n")
    merged, conflict = merge_lines(base, current, incoming)
    assert merged == current
    assert not conflict


def test_only_incoming_changed():
    base = _lines("a\nb\nc\n")
    current = _lines("a\nb\nc\n")
    incoming = _lines("a\nb\nC\n")
    merged, conflict = merge_lines(base, current, incoming)
    assert merged == incoming
    assert not conflict


def test_non_overlapping_edits_merge_cleanly():
    base = _lines("line1\nline2\nline3\nline4\nline5\n")
    current = _lines("CHANGED1\nline2\nline3\nline4\nline5\n")
    incoming = _lines("line1\nline2\nline3\nline4\nCHANGED5\n")
    merged, conflict = merge_lines(base, current, incoming)
    assert merged == _lines("CHANGED1\nline2\nline3\nline4\nCHANGED5\n")
    assert not conflict


def test_identical_edit_both_sides_no_conflict():
    base = _lines("a\nb\nc\n")
    current = _lines("a\nSAME\nc\n")
    incoming = _lines("a\nSAME\nc\n")
    merged, conflict = merge_lines(base, current, incoming)
    assert merged == current
    assert not conflict


def test_conflicting_edit_same_region():
    base = _lines("a\nb\nc\n")
    current = _lines("a\nCURRENT_VERSION\nc\n")
    incoming = _lines("a\nINCOMING_VERSION\nc\n")
    merged, conflict = merge_lines(base, current, incoming)
    assert conflict
    text = "".join(merged)
    assert "<<<<<<< CURRENT" in text
    assert "CURRENT_VERSION" in text
    assert "=======" in text
    assert "INCOMING_VERSION" in text
    assert ">>>>>>> INCOMING" in text


def test_both_sides_append_different_lines_conflict_or_merge():
    base = _lines("a\nb\n")
    current = _lines("a\nb\nfrom_current\n")
    incoming = _lines("a\nb\nfrom_incoming\n")
    merged, conflict = merge_lines(base, current, incoming)
    # Both appended different content at the same point -> conflict.
    assert conflict
    text = "".join(merged)
    assert "from_current" in text
    assert "from_incoming" in text
