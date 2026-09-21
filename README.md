# MiniGit

A lightweight Git-inspired version control system, implemented from
scratch in Python - content-addressable object store, commit DAG,
branches, staging, checkout, diff, three-way merge with conflict
detection - plus a FastAPI REST layer and an interactive React
dashboard for visualizing the repository graph.

No Git library, no shelling out to `git`, no wrapped Git internals. Every
piece here - the hashing scheme, the tree/commit model, the merge
algorithm - is built from first principles. See
[`docs/architecture.md`](docs/architecture.md) for the full design
writeup and the reasoning behind each decision.

## Why this exists

This is a portfolio project built to demonstrate systems-engineering
fundamentals that don't show up in most CRUD-app projects: content
addressing, DAG traversal, tree-diffing, and a three-way merge - the
kind of thing you'd otherwise only encounter by reading Git's source.
Every design decision below is something I can explain and defend, not
just code that happens to pass its tests.

## Architecture

```
                    CLI
                     |
                     v
              MiniGit Core  <-------- REST API (FastAPI) <---- React frontend
                     |
        +------------+-------------+
        |            |             |
        v            v             v
   Object Store   Index/Stage   Repository
        |                          |
        v                          v
   Filesystem                  Commit DAG
                                   |
                                   v
                               Branches -> Merge
```

The CLI and the REST API are both thin adapters over the same
`core.repository.Repository` class - neither contains any
version-control logic of its own. Full breakdown in
[`docs/architecture.md`](docs/architecture.md).

## Object model

Every object (blob, tree, commit) is serialized as
`"<type> <byte-length>\0<body>"` and identified by the **SHA-256** hash
of that entire byte string. Trees serialize their entries in
name-sorted order, which is what makes two identical directories always
hash identically regardless of filesystem iteration order. Full
rationale in the architecture doc.

## Repository structure

```
.minigit/
├── objects/          # content-addressable store, fan-out by oid[:2]
├── refs/heads/       # one file per branch, holding a commit oid
├── HEAD              # symbolic ref, e.g. "ref: refs/heads/main"
├── index             # staging area (flat JSON)
└── config
```

## Installation

```bash
git clone <this-repo> && cd minigit
pip install -e ".[api,dev]"
```

## CLI usage

```
minigit init [path]                 initialize a repository
minigit add <path>                  stage a file or directory
minigit status                      show staged/unstaged/untracked/deleted
minigit commit "<message>"          record staged changes
minigit log [-v]                    show commit history
minigit branch [name]               list branches, or create one
minigit checkout <branch> [--force] switch branches
minigit diff [commit]               diff working tree (or a commit) vs HEAD
minigit merge <branch>              three-way merge a branch into the current one
minigit inspect <hash>              print a raw object's contents
```

Example session:

```
$ minigit init
Initialized empty MiniGit repository in .../.minigit

$ minigit add src/
add 'src/main.py'

$ minigit commit "Initial commit"
[main a81f92c] Initial commit

$ minigit branch feature/auth
Created branch 'feature/auth'

$ minigit checkout feature/auth
Switched to branch 'feature/auth'
```

## API usage

```bash
uvicorn api.server:app --reload
```

| Method | Path                       | Purpose                          |
|--------|----------------------------|-----------------------------------|
| GET    | `/api/status`               | working tree status              |
| GET    | `/api/summary`              | dashboard overview stats          |
| GET    | `/api/branches`              | list branches                    |
| POST   | `/api/branches`              | create a branch                  |
| GET    | `/api/commits?all=true`      | commit list (all branches, or HEAD's history with `all=false`) |
| GET    | `/api/commits/{hash}`        | one commit                       |
| GET    | `/api/commits/{hash}/diff`   | structured diff vs its parent    |
| GET    | `/api/objects/{hash}`        | inspect any raw object           |
| GET    | `/api/tree/{hash}`           | tree entries                     |
| POST   | `/api/checkout`              | switch branches                  |
| POST   | `/api/merge`                 | three-way merge a branch in      |

Errors are returned as structured JSON (`{"error": "BranchNotFound",
"message": "..."}`) with the appropriate HTTP status — never a raw
Python traceback.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Proxies `/api/*` to `http://localhost:8000` by default in dev (see
`vite.config.ts`; override with `VITE_BACKEND_URL`). Three views:

- **Graph** - the commit DAG as an interactive React Flow canvas.
  Branch tips get colored labels, HEAD is badged, merge commits get a
  dashed border, and clicking a node opens the commit detail panel
  (parents, tree, "View Diff", "Inspect Object"). Includes branch
  filtering and a live search that dims non-matching commits.
- **Object Explorer** - a literal tree view of commit → tree → blob,
  lazily fetching each level as you expand it.
- **Dashboard** - repository-wide stats (commit/branch/object counts,
  current branch, latest commit).

## Merge algorithm, in short

Decided per-file first (unchanged-on-one-side wins cleanly, no line
diffing needed), and only falls through to a line-level three-way merge
when both sides actually changed the same file differently. That merge
is a from-scratch simplified diff3: independently diff base→current and
base→incoming, then merge the two change-lists over base's line
numbers, emitting `<<<<<<< CURRENT` / `=======` / `>>>>>>> INCOMING`
markers wherever both sides touched the same region with different
results. Full walkthrough with diagrams in
[`docs/architecture.md`](docs/architecture.md#8-three-way-merge).

## Testing

```bash
pip install -e ".[dev]"
pytest -q
```

82 tests covering the object store, blob/tree/commit serialization,
staging, commits, branching, checkout, persistence (close/reopen),
diff, the diff3 merge algorithm, repository-level merge (fast-forward,
clean 3-way, conflicting, resolve-and-commit), and the API (status
codes, error mapping).

## Benchmarking

```bash
python benchmarks/benchmark.py
```

No numbers are fabricated — the script measures object write/read time,
commit/checkout time, and history-traversal time on your machine, at
increasing sizes. Sample run on this development machine:

```
Object store: write/read (median of N ops)
------------------------------------------
n     write_total_s  write_per_object_us  read_total_s  read_per_object_us
100   0.0066         65.7                 0.0017        17.1
1000  0.0680         68.0                 0.0172        17.2
5000  0.3566         71.3                 0.0843        16.9

Commit + checkout (single commit, N files staged)
-------------------------------------------------
n_files  commit_s  checkout_s
10       0.0003    0.0011
100      0.0005    0.0094
500      0.0016    0.0488

History traversal (log() over N commits)
----------------------------------------
n_commits  log_s   log_per_commit_us
50         0.0010  19.3
500        0.0142  28.5
2000       0.0406  20.3
```

Per-object read/write cost stays roughly flat as the store grows (the
fan-out directory scheme doing its job), and per-commit traversal cost
in `log()` stays flat too — confirming the DAG walk is linear in commit
count rather than degrading as history grows.

## Docker

```bash
docker compose up --build
```

Runs the API on `:8000` and the built frontend on `:4173`. Set
`MINIGIT_REPO_PATH` (backend) and rebuild the frontend image with
`--build-arg VITE_API_BASE=<url>` if your API isn't on `localhost:8000`.

## Design tradeoffs

- **JSON index instead of Git's packed binary format** — far simpler to
  read, debug, and explain; the cost is a slightly larger file on disk
  and no stat-based fast-path for detecting unchanged files (MiniGit
  rehashes file content on every `status()` call instead).
- **Line-oriented three-way merge instead of a full recursive merge
  strategy** — handles the common cases correctly and is explainable in
  one sitting; no rename detection, no word-level conflicts.
- **BFS ancestor-set merge-base instead of a proper LCA algorithm** —
  correct, easy to reason about, not asymptotically optimal on very
  deep histories.

## Limitations

Not implemented, on purpose: `.minigitignore`, symlink handling,
detached HEAD at the CLI/API level, tags, stash, remotes, push/pull,
rename detection, sparse/partial checkout, packfiles (every object is
stored uncompressed and individually). This is not a production-ready
Git replacement — it's a from-scratch demonstration of the concepts
that make one work.

## Future work

- Object compression (zlib) once the "one file per object" approach
  needs to scale further.
- Rename detection in diff.
- A pluggable merge strategy interface (to compare the simplified diff3
  here against a patience-diff-based approach).
- Remote repositories over HTTP, modeled after the same content-address
  primitives already in place.
