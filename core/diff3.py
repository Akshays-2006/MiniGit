"""A simplified diff3-style line merge.

Algorithm:
    1. Diff base->current and base->incoming independently with difflib.
       Keep only the non-"equal" opcodes -- i.e. only the spans that
       actually changed relative to the common ancestor.
    2. Merge the two change-lists into a single ordered walk over base's
       line indices:
         - a span touched by only one side is applied as-is (no conflict)
         - a span touched by both sides, with identical resulting content,
           is applied once (both sides made the same edit -- no conflict)
         - a span touched by both sides with DIFFERENT resulting content
           is a conflict: both versions are wrapped in conflict markers
         - overlapping spans from the two change-lists are unioned into
           one conflict region rather than diffed line-by-line
    3. Base content untouched by either side passes through unchanged.

This is intentionally line-oriented and does not implement patience diff,
word-level conflict granularity, or Git's full recursive-merge machinery.
For a single file's history, it correctly handles the common cases: one
side edits, one side is untouched; both sides edit non-overlapping
regions; both sides make the identical edit; both sides edit the same
region differently (conflict). See docs/architecture.md for the tradeoff.
"""

from __future__ import annotations

import difflib

CONFLICT_START = "<<<<<<< CURRENT\n"
CONFLICT_MID = "=======\n"
CONFLICT_END = ">>>>>>> INCOMING\n"


def _opcodes(base: list[str], other: list[str]):
    sm = difflib.SequenceMatcher(None, base, other, autojunk=False)
    return sm.get_opcodes()


def merge_lines(
    base: list[str], current: list[str], incoming: list[str]
) -> tuple[list[str], bool]:
    """Return (merged_lines, has_conflict)."""
    current_ops = [op for op in _opcodes(base, current) if op[0] != "equal"]
    incoming_ops = [op for op in _opcodes(base, incoming) if op[0] != "equal"]

    events = []  # [i1, i2, side, j1, j2]
    for _tag, i1, i2, j1, j2 in current_ops:
        events.append([i1, i2, "current", j1, j2])
    for _tag, i1, i2, j1, j2 in incoming_ops:
        events.append([i1, i2, "incoming", j1, j2])
    events.sort(key=lambda e: e[0])

    merged: list[str] = []
    has_conflict = False
    base_pos = 0
    idx = 0
    n_events = len(events)

    while idx < n_events:
        i1, i2, _side, _j1, _j2 = events[idx]

        # Pass through unchanged base content before this event.
        if i1 > base_pos:
            merged.extend(base[base_pos:i1])
            base_pos = i1

        # Union every event overlapping this base range into one group.
        # Two zero-width insertions (i1 == i2) at the exact same base
        # position are also grouped together -- both sides inserting at
        # the same point is exactly the case a 3-way merge must flag as
        # a conflict rather than silently picking an order.
        group_start = i1
        group = [events[idx]]
        group_end = i2
        idx += 1
        while idx < n_events and (events[idx][0] < group_end or events[idx][0] == group_start):
            group_end = max(group_end, events[idx][1])
            group.append(events[idx])
            idx += 1

        sides_present = {g[2] for g in group}
        current_group = [g for g in group if g[2] == "current"]
        incoming_group = [g for g in group if g[2] == "incoming"]

        if sides_present == {"current"}:
            for g in current_group:
                merged.extend(current[g[3]:g[4]])
        elif sides_present == {"incoming"}:
            for g in incoming_group:
                merged.extend(incoming[g[3]:g[4]])
        else:
            current_lines = []
            for g in current_group:
                current_lines.extend(current[g[3]:g[4]])
            incoming_lines = []
            for g in incoming_group:
                incoming_lines.extend(incoming[g[3]:g[4]])

            if current_lines == incoming_lines:
                merged.extend(current_lines)
            else:
                has_conflict = True
                merged.append(CONFLICT_START)
                merged.extend(current_lines)
                merged.append(CONFLICT_MID)
                merged.extend(incoming_lines)
                merged.append(CONFLICT_END)

        base_pos = max(base_pos, group_end)

    if base_pos < len(base):
        merged.extend(base[base_pos:])

    return merged, has_conflict
