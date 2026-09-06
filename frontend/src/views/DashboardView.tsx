import type { Summary, BranchList } from "../api/client";
import "./DashboardView.css";

export function DashboardView({ summary, branches }: { summary: Summary | null; branches: BranchList | null }) {
  if (!summary) {
    return <div className="dashboard dashboard--empty">Loading repository…</div>;
  }

  const worktreeName = summary.worktree.split("/").filter(Boolean).pop() ?? summary.worktree;

  return (
    <div className="dashboard">
      <div className="dashboard__header">
        <h1 className="dashboard__name">{worktreeName}</h1>
        <p className="dashboard__path mono">{summary.worktree}</p>
      </div>

      <div className="dashboard__grid">
        <div className="dashboard__stat">
          <span className="dashboard__stat-value">{summary.commit_count}</span>
          <span className="dashboard__stat-label">commits</span>
        </div>
        <div className="dashboard__stat">
          <span className="dashboard__stat-value">{summary.branch_count}</span>
          <span className="dashboard__stat-label">branches</span>
        </div>
        <div className="dashboard__stat">
          <span className="dashboard__stat-value">{summary.object_count}</span>
          <span className="dashboard__stat-label">objects</span>
        </div>
      </div>

      <div className="dashboard__row">
        <div className="dashboard__field">
          <span className="dashboard__field-label">Current branch</span>
          <span className="dashboard__field-value">{summary.branch}</span>
        </div>
        <div className="dashboard__field">
          <span className="dashboard__field-label">HEAD</span>
          <span className="dashboard__field-value mono">
            {summary.head ? summary.head.slice(0, 12) : "(no commits)"}
          </span>
        </div>
      </div>

      {summary.latest_message && (
        <div className="dashboard__latest">
          <span className="dashboard__field-label">Latest commit</span>
          <p className="dashboard__latest-message">{summary.latest_message}</p>
        </div>
      )}

      {branches && branches.branches.length > 0 && (
        <div className="dashboard__branches">
          <span className="dashboard__field-label">All branches</span>
          <ul>
            {branches.branches.map((b) => (
              <li key={b.name}>
                <span className={b.name === branches.current ? "dashboard__branch-current" : ""}>{b.name}</span>
                <span className="mono dashboard__branch-commit">{b.commit.slice(0, 10)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
