import { useState } from "react";
import { api, type CommitSummary, type DiffResult } from "../api/client";
import "./CommitDetailPanel.css";

function formatTimestamp(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

function DiffHunks({ hunks }: { hunks: string[] }) {
  return (
    <pre className="diff-block mono">
      {hunks.map((line, i) => {
        let cls = "diff-line";
        if (line.startsWith("+") && !line.startsWith("+++")) cls += " diff-line--add";
        else if (line.startsWith("-") && !line.startsWith("---")) cls += " diff-line--del";
        else if (line.startsWith("@@")) cls += " diff-line--hunk";
        return (
          <div key={i} className={cls}>
            {line.replace(/\n$/, "")}
          </div>
        );
      })}
    </pre>
  );
}

export function CommitDetailPanel({
  commit,
  onClose,
  onInspect,
}: {
  commit: CommitSummary;
  onClose: () => void;
  onInspect: (hash: string) => void;
}) {
  const [diff, setDiff] = useState<DiffResult | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [loadingDiff, setLoadingDiff] = useState(false);

  const loadDiff = async () => {
    setShowDiff(true);
    if (diff) return;
    setLoadingDiff(true);
    try {
      const result = await api.getCommitDiff(commit.hash);
      setDiff(result);
    } finally {
      setLoadingDiff(false);
    }
  };

  const changedCount = diff ? diff.added.length + diff.deleted.length + diff.modified.length : null;

  return (
    <aside className="detail-panel">
      <div className="detail-panel__header">
        <span className="detail-panel__title mono">{commit.short_hash}</span>
        <button className="detail-panel__close" onClick={onClose} aria-label="Close panel">
          ×
        </button>
      </div>

      <div className="detail-panel__body">
        <p className="detail-panel__message">{commit.message}</p>

        <dl className="detail-panel__meta">
          <dt>Author</dt>
          <dd>{commit.author}</dd>
          <dt>Date</dt>
          <dd>{formatTimestamp(commit.timestamp)}</dd>
          <dt>Tree</dt>
          <dd>
            <button className="detail-panel__link mono" onClick={() => onInspect(commit.tree)}>
              {commit.tree.slice(0, 12)}…
            </button>
          </dd>
          <dt>{commit.parents.length > 1 ? "Parents" : "Parent"}</dt>
          <dd>
            {commit.parents.length === 0 && <span className="detail-panel__muted">(root commit)</span>}
            {commit.parents.map((p) => (
              <button key={p} className="detail-panel__link mono" onClick={() => onInspect(p)}>
                {p.slice(0, 7)}
              </button>
            ))}
          </dd>
          <dt>Hash</dt>
          <dd className="mono detail-panel__full-hash">{commit.hash}</dd>
        </dl>

        <div className="detail-panel__actions">
          <button className="detail-panel__button" onClick={loadDiff}>
            View diff
          </button>
          <button className="detail-panel__button detail-panel__button--ghost" onClick={() => onInspect(commit.hash)}>
            Inspect object
          </button>
        </div>

        {showDiff && (
          <div className="detail-panel__diff">
            {loadingDiff && <p className="detail-panel__muted">Loading diff…</p>}
            {diff && (
              <>
                <p className="detail-panel__muted">
                  {changedCount === 0 ? "No changes" : `${changedCount} file${changedCount === 1 ? "" : "s"} changed`}
                </p>
                {diff.added.map((path) => (
                  <div key={path} className="diff-file diff-file--added">
                    + {path}
                  </div>
                ))}
                {diff.deleted.map((path) => (
                  <div key={path} className="diff-file diff-file--deleted">
                    − {path}
                  </div>
                ))}
                {diff.modified.map((entry) => (
                  <div key={entry.path} className="diff-file diff-file--modified">
                    <div className="diff-file__path">{entry.path}</div>
                    <DiffHunks hunks={entry.hunks} />
                  </div>
                ))}
              </>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
