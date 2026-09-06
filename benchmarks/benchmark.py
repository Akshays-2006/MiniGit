"""Benchmark MiniGit's core operations at increasing repository sizes.

Run directly:

    python benchmarks/benchmark.py

Every number printed is measured on this machine, right now -- nothing
here is a fabricated or extrapolated figure. Re-run it yourself; your
numbers will differ by hardware, but the *shape* (how each operation
scales with N) should look similar.

What's measured, and why these specifically:
    - object write/read time  -> is the content-addressable store itself
      a bottleneck as the object count grows?
    - commit creation time    -> does building+writing a tree from the
      index scale with file count?
    - history traversal time  -> does `log_all_branches` (a DAG walk)
      stay linear in commit count?
    - checkout time           -> does reconstructing a working tree from
      a tree object scale with file count?
"""

from __future__ import annotations

import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.checkout import checkout_branch
from core.repository import Repository


def timed(fn, repeat: int = 3) -> float:
    """Return the median wall-clock time (seconds) of `repeat` runs."""
    samples = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


def benchmark_object_store(n: int) -> dict:
    tmp = Path(tempfile.mkdtemp())
    try:
        repo = Repository.init(tmp)
        payloads = [f"benchmark payload number {i}".encode() * 5 for i in range(n)]

        write_time = timed(lambda: [repo.store.write("blob", p) for p in payloads], repeat=1)
        oids = [repo.store.write("blob", p) for p in payloads]
        read_time = timed(lambda: [repo.store.read(oid) for oid in oids], repeat=3)

        return {
            "n": n,
            "write_total_s": write_time,
            "write_per_object_us": (write_time / n) * 1e6,
            "read_total_s": read_time,
            "read_per_object_us": (read_time / n) * 1e6,
        }
    finally:
        shutil.rmtree(tmp)


def benchmark_commit_and_checkout(n_files: int) -> dict:
    tmp = Path(tempfile.mkdtemp())
    try:
        repo = Repository.init(tmp)
        for i in range(n_files):
            (tmp / f"file_{i}.txt").write_text(f"content {i}")
            repo.add_path(f"file_{i}.txt")

        already_committed = repo.refs.get_head_commit() is not None
        message = f"commit with {n_files} files"
        commit_time = timed(lambda: None if already_committed else repo.commit(message), repeat=1)
        if repo.refs.get_head_commit() is None:
            repo.commit(message)

        repo.create_branch("bench-branch")

        def do_checkout():
            checkout_branch(repo, "bench-branch", force=True)
            checkout_branch(repo, "main", force=True)

        checkout_time = timed(do_checkout, repeat=3) / 2  # two checkouts per call

        return {"n_files": n_files, "commit_s": commit_time, "checkout_s": checkout_time}
    finally:
        shutil.rmtree(tmp)


def benchmark_history_traversal(n_commits: int) -> dict:
    tmp = Path(tempfile.mkdtemp())
    try:
        repo = Repository.init(tmp)
        (tmp / "a.txt").write_text("v0")
        repo.add_path("a.txt")
        repo.commit("initial")
        for i in range(1, n_commits):
            (tmp / "a.txt").write_text(f"v{i}")
            repo.add_path("a.txt")
            repo.commit(f"commit {i}")

        log_time = timed(lambda: repo.log(), repeat=5)
        return {
            "n_commits": n_commits,
            "log_s": log_time,
            "log_per_commit_us": (log_time / n_commits) * 1e6,
        }
    finally:
        shutil.rmtree(tmp)


def print_table(title: str, rows: list[dict]):
    print(f"\n{title}")
    print("-" * len(title))
    if not rows:
        return
    headers = list(rows[0].keys())

    def cell(row: dict, key: str) -> str:
        value = row[key]
        return f"{value:.4f}" if isinstance(value, float) else str(value)

    widths = [max(len(h), *(len(cell(r, h)) for r in rows)) for h in headers]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True)))
    for r in rows:
        cells = [cell(r, h) for h in headers]
        print("  ".join(c.ljust(w) for c, w in zip(cells, widths, strict=True)))


if __name__ == "__main__":
    sizes = [100, 1_000, 5_000]
    object_rows = [benchmark_object_store(n) for n in sizes]
    print_table("Object store: write/read (median of N ops)", object_rows)

    commit_rows = [benchmark_commit_and_checkout(n) for n in [10, 100, 500]]
    print_table("Commit + checkout (single commit, N files staged)", commit_rows)

    history_rows = [benchmark_history_traversal(n) for n in [50, 500, 2000]]
    print_table("History traversal (log() over N commits)", history_rows)
