import { useCallback, useEffect, useState } from "react";
import { api, MiniGitApiError, setActiveRepoPath, type BranchList, type CommitSummary, type Summary } from "./api/client";
import { Sidebar } from "./components/Sidebar";
import { CommitDetailPanel } from "./components/CommitDetailPanel";
import { ObjectExplorer } from "./components/ObjectExplorer";
import { GraphView } from "./views/GraphView";
import { DashboardView } from "./views/DashboardView";
import "./App.css";

type Tab = "graph" | "objects" | "dashboard";

const LAST_REPO_STORAGE_KEY = "minigit:lastRepoPath";

export default function App() {
  const [tab, setTab] = useState<Tab>("graph");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [branches, setBranches] = useState<BranchList | null>(null);
  const [commits, setCommits] = useState<CommitSummary[]>([]);
  const [selectedCommit, setSelectedCommit] = useState<CommitSummary | null>(null);
  const [inspectHash, setInspectHash] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [checkingOut, setCheckingOut] = useState<string | null>(null);
  const [loadingRepo, setLoadingRepo] = useState(false);
  const [banner, setBanner] = useState<{ kind: "error" | "info"; text: string } | null>(null);

  const refresh = useCallback(async () => {
    const [s, b, c] = await Promise.all([api.getSummary(), api.getBranches(), api.getCommits()]);
    setSummary(s);
    setBranches(b);
    setCommits(c);
  }, []);

  // On first load, resume whichever repo the user had open last time (if
  // any) -- otherwise fall through to the backend's own default (the
  // MINIGIT_REPO_PATH env var it was started with, or its cwd).
  useEffect(() => {
    const lastPath = window.localStorage.getItem(LAST_REPO_STORAGE_KEY);
    if (lastPath) setActiveRepoPath(lastPath);
    refresh().catch((e) => {
      const msg = e instanceof MiniGitApiError ? e.message : "Failed to load repository";
      setBanner({ kind: "error", text: msg });
    });
  }, [refresh]);

  const handleSelectCommit = useCallback(
    (hash: string) => {
      const commit = commits.find((c) => c.hash === hash);
      if (commit) setSelectedCommit(commit);
    },
    [commits]
  );

  const handleInspect = useCallback((hash: string) => {
    setInspectHash(hash);
    setTab("objects");
  }, []);

  const handleOpenRepo = async (path: string) => {
    setLoadingRepo(true);
    setBanner(null);
    const previousPath = summary?.worktree ?? null;
    setActiveRepoPath(path);
    try {
      await refresh();
      window.localStorage.setItem(LAST_REPO_STORAGE_KEY, path);
      setSelectedCommit(null);
      setInspectHash(null);
    } catch (e) {
      // Roll back so subsequent calls don't keep hitting a bad path.
      setActiveRepoPath(previousPath);
      const msg =
        e instanceof MiniGitApiError && e.errorType === "RepositoryNotFound"
          ? `No MiniGit repository found at '${path}' (or any parent directory).`
          : e instanceof MiniGitApiError
            ? e.message
            : "Failed to open repository";
      setBanner({ kind: "error", text: msg });
    } finally {
      setLoadingRepo(false);
    }
  };

  const handleCheckout = async (branch: string) => {
    setCheckingOut(branch);
    setBanner(null);
    try {
      await api.checkout(branch);
      await refresh();
      setSelectedCommit(null);
    } catch (e) {
      const msg = e instanceof MiniGitApiError ? e.message : "Checkout failed";
      setBanner({ kind: "error", text: msg });
    } finally {
      setCheckingOut(null);
    }
  };

  const handleMerge = async (branch: string) => {
    setBanner(null);
    try {
      const result = await api.merge(branch);
      await refresh();
      if (result.status === "conflict") {
        const files = (result.conflicted_files as string[]).join(", ");
        setBanner({ kind: "error", text: `Merge conflict in: ${files}. Resolve on disk, then commit.` });
      } else if (result.status === "already_up_to_date") {
        setBanner({ kind: "info", text: `Already up to date with '${branch}'.` });
      } else {
        setBanner({ kind: "info", text: `Merged '${branch}' successfully.` });
      }
    } catch (e) {
      const msg = e instanceof MiniGitApiError ? e.message : "Merge failed";
      setBanner({ kind: "error", text: msg });
    }
  };

  return (
    <div className="app">
      <Sidebar
        summary={summary}
        branches={branches}
        onCheckout={handleCheckout}
        onMerge={handleMerge}
        onOpenRepo={handleOpenRepo}
        checkingOut={checkingOut}
        isOpeningRepo={loadingRepo}
      />

      <div className="app__main">
        <div className="app__topbar">
          <nav className="app__tabs">
            {(["graph", "objects", "dashboard"] as Tab[]).map((t) => (
              <button
                key={t}
                className={`app__tab${tab === t ? " app__tab--active" : ""}`}
                onClick={() => setTab(t)}
              >
                {t === "graph" ? "Graph" : t === "objects" ? "Object Explorer" : "Dashboard"}
              </button>
            ))}
          </nav>
          {tab === "graph" && (
            <input
              className="app__search"
              placeholder="Search commits…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          )}
        </div>

        {banner && (
          <div className={`app__banner app__banner--${banner.kind}`}>
            {banner.text}
            <button className="app__banner-dismiss" onClick={() => setBanner(null)} aria-label="Dismiss">
              ×
            </button>
          </div>
        )}

        <div className="app__content">
          {tab === "graph" && (
            <GraphView commits={commits} branches={branches} onSelectCommit={handleSelectCommit} searchQuery={searchQuery} />
          )}
          {tab === "objects" && (
            <ObjectExplorer
              rootHash={inspectHash ?? summary?.head ?? ""}
              rootName={inspectHash ? "object" : "HEAD commit"}
            />
          )}
          {tab === "dashboard" && <DashboardView summary={summary} branches={branches} />}

          {tab === "graph" && selectedCommit && (
            <CommitDetailPanel
              key={selectedCommit.hash}
              commit={selectedCommit}
              onClose={() => setSelectedCommit(null)}
              onInspect={handleInspect}
            />
          )}
        </div>
      </div>
    </div>
  );
}
