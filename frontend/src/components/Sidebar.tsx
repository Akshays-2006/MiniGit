import type { BranchList, Summary } from "../api/client";
import { RepoSwitcher } from "./RepoSwitcher";
import "./Sidebar.css";

export function Sidebar({
  summary,
  branches,
  onCheckout,
  onMerge,
  onOpenRepo,
  checkingOut,
  isOpeningRepo,
}: {
  summary: Summary | null;
  branches: BranchList | null;
  onCheckout: (name: string) => void;
  onMerge: (name: string) => void;
  onOpenRepo: (path: string) => void;
  checkingOut: string | null;
  isOpeningRepo: boolean;
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__brand-mark" aria-hidden="true" />
        MiniGit
      </div>

      <RepoSwitcher currentWorktree={summary?.worktree ?? null} onOpen={onOpenRepo} isLoading={isOpeningRepo} />

      {summary && (
        <div className="sidebar__section">
          <div className="sidebar__stat">
            <span className="sidebar__stat-value">{summary.commit_count}</span>
            <span className="sidebar__stat-label">commits</span>
          </div>
          <div className="sidebar__stat">
            <span className="sidebar__stat-value">{summary.branch_count}</span>
            <span className="sidebar__stat-label">branches</span>
          </div>
          <div className="sidebar__stat">
            <span className="sidebar__stat-value">{summary.object_count}</span>
            <span className="sidebar__stat-label">objects</span>
          </div>
        </div>
      )}

      <div className="sidebar__section">
        <div className="sidebar__heading">Branches</div>
        <ul className="sidebar__branch-list">
          {branches?.branches.map((b) => {
            const isCurrent = b.name === branches.current;
            return (
              <li key={b.name} className={`sidebar__branch${isCurrent ? " sidebar__branch--current" : ""}`}>
                <button
                  className="sidebar__branch-name"
                  onClick={() => onCheckout(b.name)}
                  disabled={isCurrent || checkingOut !== null}
                >
                  {isCurrent && <span className="sidebar__branch-dot" aria-hidden="true" />}
                  {b.name}
                </button>
                {!isCurrent && (
                  <button
                    className="sidebar__branch-merge"
                    onClick={() => onMerge(b.name)}
                    disabled={checkingOut !== null}
                    title={`Merge '${b.name}' into '${branches.current}'`}
                  >
                    merge in
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </div>

      {summary?.latest_message && (
        <div className="sidebar__section sidebar__section--footer">
          <div className="sidebar__heading">Latest</div>
          <div className="sidebar__latest-message">{summary.latest_message}</div>
        </div>
      )}
    </aside>
  );
}
