import type { CommitSummary, BranchInfo } from "../api/client";

export interface LaidOutCommit {
  commit: CommitSummary;
  column: number; // x position: topological generation, oldest to newest
  lane: number; // y position: which horizontal track this commit sits on
}

export interface GraphLayout {
  nodes: LaidOutCommit[];
  laneCount: number;
}

/**
 * Assigns each commit a (column, lane).
 *
 * Column = position in a topological ordering (parents always come before
 * children), oldest first -- this is what makes edges always point
 * left-to-right rather than crossing back on themselves.
 *
 * Lane = a horizontal track, assigned greedily walking oldest to newest.
 * A commit continues its first parent's lane ONLY if that parent is the
 * most recent thing placed in that lane -- i.e. no sibling has already
 * forked off it. That "most recent occupant" check (not just "was this
 * lane touched near this column") is what correctly gives a second child
 * of the same parent (a real fork point) its own lane instead of
 * silently overlapping the first child's line. Lanes are never recycled
 * once a branch moves off them, trading some extra vertical space for an
 * algorithm simple enough to fully hold in your head.
 */
export function layoutCommitGraph(commits: CommitSummary[], branches: BranchInfo[]): GraphLayout {
  const byHash = new Map(commits.map((c) => [c.hash, c]));

  // Topological order: parents are always created before their children,
  // so sorting by creation timestamp gives a valid topological order
  // without needing a separate Kahn's-algorithm pass.
  const ordered = [...commits].sort((a, b) => a.timestamp - b.timestamp);

  const columnOf = new Map<string, number>();
  ordered.forEach((c, i) => columnOf.set(c.hash, i));

  // Branch tips get priority for lane 0 by name (main first) so the
  // primary branch reads as a straight horizontal line.
  const tipOrder = [...branches].sort((a, b) =>
    a.name === "main" ? -1 : b.name === "main" ? 1 : a.name.localeCompare(b.name)
  );
  const tipToPreferredLane = new Map<string, number>();
  tipOrder.forEach((b, i) => tipToPreferredLane.set(b.commit, i));

  const laneOfCommit = new Map<string, number>();
  const lastCommitInLane: (string | undefined)[] = []; // lane -> oid of the most recent commit placed there

  const claimNewLane = (hash: string): number => {
    const preferred = tipToPreferredLane.get(hash);
    if (preferred !== undefined && lastCommitInLane[preferred] === undefined) {
      return preferred;
    }
    return lastCommitInLane.length;
  };

  for (const commit of ordered) {
    const firstParent = commit.parents.find((p) => byHash.has(p));
    const parentLane = firstParent !== undefined ? laneOfCommit.get(firstParent) : undefined;

    const lane =
      parentLane !== undefined && lastCommitInLane[parentLane] === firstParent
        ? parentLane
        : claimNewLane(commit.hash);

    laneOfCommit.set(commit.hash, lane);
    lastCommitInLane[lane] = commit.hash;
  }

  const laneCount = lastCommitInLane.length;
  const nodes: LaidOutCommit[] = ordered.map((commit) => ({
    commit,
    column: columnOf.get(commit.hash)!,
    lane: laneOfCommit.get(commit.hash)!,
  }));

  return { nodes, laneCount };
}
