import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ReactFlowProvider } from "reactflow";
import { CommitNode } from "./CommitNode";
import type { CommitSummary } from "../api/client";

const baseCommit: CommitSummary = {
  hash: "a".repeat(64),
  short_hash: "aaaaaaa",
  tree: "t".repeat(64),
  parents: [],
  author: "Akshay <a@example.com>",
  timestamp: 0,
  message: "Initial commit",
};

function renderNode(overrides: Partial<Parameters<typeof CommitNode>[0]["data"]> = {}) {
  const onSelect = vi.fn();
  render(
    <ReactFlowProvider>
      <CommitNode
        data={{
          commit: baseCommit,
          branchLabels: [],
          isHead: false,
          isMerge: false,
          onSelect,
          ...overrides,
        }}
      />
    </ReactFlowProvider>
  );
  return { onSelect };
}

describe("CommitNode", () => {
  it("shows the short hash and first line of the message", () => {
    renderNode();
    expect(screen.getByText("aaaaaaa")).toBeInTheDocument();
    expect(screen.getByText("Initial commit")).toBeInTheDocument();
  });

  it("only shows the first line of a multi-line message", () => {
    renderNode({ commit: { ...baseCommit, message: "Title line\n\nBody detail" } });
    expect(screen.getByText("Title line")).toBeInTheDocument();
    expect(screen.queryByText(/Body detail/)).not.toBeInTheDocument();
  });

  it("shows a HEAD badge only when isHead is true", () => {
    renderNode({ isHead: true });
    expect(screen.getByText("HEAD")).toBeInTheDocument();
  });

  it("renders branch labels as pills", () => {
    renderNode({ branchLabels: ["main", "feature/auth"] });
    expect(screen.getByText("main")).toBeInTheDocument();
    expect(screen.getByText("feature/auth")).toBeInTheDocument();
  });

  it("calls onSelect with the commit hash when clicked", () => {
    const { onSelect } = renderNode();
    fireEvent.click(screen.getByText("Initial commit").closest(".commit-node")!);
    expect(onSelect).toHaveBeenCalledWith(baseCommit.hash);
  });

  it("calls onSelect on Enter key for keyboard accessibility", () => {
    const { onSelect } = renderNode();
    const node = screen.getByText("Initial commit").closest(".commit-node")!;
    fireEvent.keyDown(node, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith(baseCommit.hash);
  });
});
