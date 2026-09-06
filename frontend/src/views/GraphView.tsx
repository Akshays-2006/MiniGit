import { useMemo, useState, useCallback } from "react";
import ReactFlow, { Background, Controls, type Edge, type Node, MarkerType } from "reactflow";
import "reactflow/dist/style.css";
import type { BranchList, CommitSummary } from "../api/client";
import { layoutCommitGraph } from "../api/layout";
import { CommitNode } from "../components/CommitNode";
import "./GraphView.css";

const COLUMN_WIDTH = 260;
const LANE_HEIGHT = 110;

const nodeTypes = { commit: CommitNode };

export function GraphView({
  commits,
  branches,
  onSelectCommit,
  searchQuery,
}: {
  commits: CommitSummary[];
  branches: BranchList | null;
  onSelectCommit: (hash: string) => void;
  searchQuery: string;
}) {
  const [branchFilter, setBranchFilter] = useState<string | null>(null);

  const filteredCommits = useMemo(() => {
    if (!branchFilter || !branches) return commits;
    // A commit belongs to a branch's graph if it's an ancestor of that
    // branch's tip. Cheap approximation for the filter UI: walk parents.
    const tipHash = branches.branches.find((b) => b.name === branchFilter)?.commit;
    if (!tipHash) return commits;
    const byHash = new Map(commits.map((c) => [c.hash, c]));
    const included = new Set<string>();
    const stack = [tipHash];
    while (stack.length) {
      const h = stack.pop()!;
      if (included.has(h)) continue;
      included.add(h);
      const c = byHash.get(h);
      if (c) stack.push(...c.parents);
    }
    return commits.filter((c) => included.has(c.hash));
  }, [commits, branchFilter, branches]);

  const { nodes, edges } = useMemo(() => {
    const layout = layoutCommitGraph(filteredCommits, branches?.branches ?? []);
    const branchLabelsByCommit = new Map<string, string[]>();
    for (const b of branches?.branches ?? []) {
      const list = branchLabelsByCommit.get(b.commit) ?? [];
      list.push(b.name);
      branchLabelsByCommit.set(b.commit, list);
    }

    const query = searchQuery.trim().toLowerCase();

    const rfNodes: Node[] = layout.nodes.map(({ commit, column, lane }) => {
      const matchesSearch =
        query.length > 0 &&
        (commit.message.toLowerCase().includes(query) ||
          commit.hash.toLowerCase().includes(query) ||
          commit.author.toLowerCase().includes(query));
      return {
        id: commit.hash,
        type: "commit",
        position: { x: column * COLUMN_WIDTH, y: lane * LANE_HEIGHT },
        data: {
          commit,
          branchLabels: branchLabelsByCommit.get(commit.hash) ?? [],
          isHead: commit.hash === branches?.branches.find((b) => b.name === branches.current)?.commit,
          isMerge: commit.parents.length > 1,
          onSelect: onSelectCommit,
        },
        style: query.length > 0 ? { opacity: matchesSearch ? 1 : 0.25 } : undefined,
        draggable: false,
      };
    });

    const rfEdges: Edge[] = [];
    for (const { commit } of layout.nodes) {
      for (const parent of commit.parents) {
        if (!filteredCommits.find((c) => c.hash === parent)) continue;
        rfEdges.push({
          id: `${parent}-${commit.hash}`,
          source: parent,
          target: commit.hash,
          type: "smoothstep",
          style: { stroke: "var(--hairline)", strokeWidth: 1.5 },
          markerEnd: { type: MarkerType.ArrowClosed, color: "var(--hairline)", width: 14, height: 14 },
        });
      }
    }

    return { nodes: rfNodes, edges: rfEdges };
  }, [filteredCommits, branches, onSelectCommit, searchQuery]);

  const onInit = useCallback((instance: { fitView: () => void }) => {
    instance.fitView();
  }, []);

  if (commits.length === 0) {
    return (
      <div className="graph-view graph-view--empty">
        <p>No commits yet. Run <code className="mono">minigit commit</code> to start the graph.</p>
      </div>
    );
  }

  return (
    <div className="graph-view">
      <div className="graph-view__filters">
        <button
          className={`graph-view__filter-pill${branchFilter === null ? " graph-view__filter-pill--active" : ""}`}
          onClick={() => setBranchFilter(null)}
        >
          all branches
        </button>
        {branches?.branches.map((b) => (
          <button
            key={b.name}
            className={`graph-view__filter-pill${branchFilter === b.name ? " graph-view__filter-pill--active" : ""}`}
            onClick={() => setBranchFilter(b.name)}
          >
            {b.name}
          </button>
        ))}
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onInit={onInit}
        proOptions={{ hideAttribution: true }}
        minZoom={0.2}
        maxZoom={1.5}
        fitView
      >
        <Background color="var(--hairline)" gap={24} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
