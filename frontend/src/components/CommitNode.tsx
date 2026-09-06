import { Handle, Position } from "reactflow";
import type { CommitSummary } from "../api/client";
import "./CommitNode.css";

export interface CommitNodeData {
  commit: CommitSummary;
  branchLabels: string[];
  isHead: boolean;
  isMerge: boolean;
  onSelect: (hash: string) => void;
}

export function CommitNode({ data }: { data: CommitNodeData }) {
  const { commit, branchLabels, isHead, isMerge, onSelect } = data;

  return (
    <div
      className={`commit-node${isMerge ? " commit-node--merge" : ""}`}
      onClick={() => onSelect(commit.hash)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onSelect(commit.hash);
      }}
    >
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />

      <div className="commit-node__dot" aria-hidden="true" />
      <div className="commit-node__body">
        <div className="commit-node__row">
          <span className="commit-node__hash mono">{commit.short_hash}</span>
          {isHead && <span className="commit-node__head">HEAD</span>}
        </div>
        <div className="commit-node__message" title={commit.message}>
          {commit.message.split("\n")[0]}
        </div>
        {branchLabels.length > 0 && (
          <div className="commit-node__branches">
            {branchLabels.map((b) => (
              <span key={b} className="commit-node__branch-pill">
                {b}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
