import { describe, expect, it } from "vitest";
import { layoutCommitGraph } from "./layout";
import type { CommitSummary, BranchInfo } from "./client";

function commit(hash: string, parents: string[], timestamp: number, message = hash): CommitSummary {
  return {
    hash,
    short_hash: hash.slice(0, 7),
    tree: "t".repeat(64),
    parents,
    author: "test",
    timestamp,
    message,
  };
}

describe("layoutCommitGraph", () => {
  it("orders a linear history left to right by creation time", () => {
    const commits = [
      commit("c3", ["c2"], 3),
      commit("c1", [], 1),
      commit("c2", ["c1"], 2),
    ];
    const { nodes } = layoutCommitGraph(commits, []);
    const byHash = Object.fromEntries(nodes.map((n) => [n.commit.hash, n]));

    expect(byHash["c1"].column).toBeLessThan(byHash["c2"].column);
    expect(byHash["c2"].column).toBeLessThan(byHash["c3"].column);
  });

  it("keeps a single linear branch in one lane", () => {
    const commits = [commit("c1", [], 1), commit("c2", ["c1"], 2), commit("c3", ["c2"], 3)];
    const { nodes } = layoutCommitGraph(commits, []);
    const lanes = new Set(nodes.map((n) => n.lane));
    expect(lanes.size).toBe(1);
  });

  it("gives a diverging branch its own lane", () => {
    // c1 -> c2 -> c3 (main)
    //         \-> c4 (feature)
    const commits = [
      commit("c1", [], 1),
      commit("c2", ["c1"], 2),
      commit("c3", ["c2"], 3),
      commit("c4", ["c2"], 3.5),
    ];
    const branches: BranchInfo[] = [
      { name: "main", commit: "c3" },
      { name: "feature", commit: "c4" },
    ];
    const { nodes, laneCount } = layoutCommitGraph(commits, branches);
    const byHash = Object.fromEntries(nodes.map((n) => [n.commit.hash, n]));

    expect(laneCount).toBeGreaterThanOrEqual(2);
    expect(byHash["c3"].lane).not.toBe(byHash["c4"].lane);
    // Shared history stays on one lane up to the fork point.
    expect(byHash["c1"].lane).toBe(byHash["c2"].lane);
  });

  it("places main's tip in lane 0 when main is among the branches", () => {
    const commits = [
      commit("c1", [], 1),
      commit("c2", ["c1"], 2),
      commit("c3", ["c1"], 2.5),
    ];
    const branches: BranchInfo[] = [
      { name: "zzz-branch", commit: "c3" },
      { name: "main", commit: "c2" },
    ];
    const { nodes } = layoutCommitGraph(commits, branches);
    const byHash = Object.fromEntries(nodes.map((n) => [n.commit.hash, n]));
    expect(byHash["c2"].lane).toBe(0);
  });

  it("positions a merge commit after both of its parents", () => {
    // c1 -> c2 -> c4 (merge of c2, c3)
    //   \-> c3 ----^
    const commits = [
      commit("c1", [], 1),
      commit("c2", ["c1"], 2),
      commit("c3", ["c1"], 2.2),
      commit("c4", ["c2", "c3"], 3),
    ];
    const { nodes } = layoutCommitGraph(commits, []);
    const byHash = Object.fromEntries(nodes.map((n) => [n.commit.hash, n]));

    expect(byHash["c4"].column).toBeGreaterThan(byHash["c2"].column);
    expect(byHash["c4"].column).toBeGreaterThan(byHash["c3"].column);
  });

  it("handles an empty commit list without throwing", () => {
    const { nodes, laneCount } = layoutCommitGraph([], []);
    expect(nodes).toEqual([]);
    expect(laneCount).toBe(0);
  });
});
