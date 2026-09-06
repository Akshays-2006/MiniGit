import { useState } from "react";
import "./RepoSwitcher.css";

export function RepoSwitcher({
  currentWorktree,
  onOpen,
  isLoading,
}: {
  currentWorktree: string | null;
  onOpen: (path: string) => void;
  isLoading: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  const startEditing = () => {
    setDraft(currentWorktree ?? "");
    setEditing(true);
  };

  const submit = () => {
    if (draft.trim().length === 0) return;
    onOpen(draft.trim());
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="repo-switcher repo-switcher--editing">
        <input
          className="repo-switcher__input mono"
          autoFocus
          value={draft}
          placeholder="/path/to/repo"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
            if (e.key === "Escape") setEditing(false);
          }}
        />
        <button className="repo-switcher__button" onClick={submit} disabled={isLoading}>
          Open
        </button>
        <button className="repo-switcher__button repo-switcher__button--ghost" onClick={() => setEditing(false)}>
          Cancel
        </button>
      </div>
    );
  }

  return (
    <button className="repo-switcher" onClick={startEditing} title="Switch to a different repository">
      <span className="repo-switcher__label">Repository</span>
      <span className="repo-switcher__path mono">{currentWorktree ?? "(none loaded)"}</span>
    </button>
  );
}
