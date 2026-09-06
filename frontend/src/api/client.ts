// Thin typed wrapper over the FastAPI backend. No business logic lives
// here -- every function is a direct 1:1 call to one endpoint. The graph
// layout, panel state, etc. all live in the views/components that call these.
//
// Empty string -> relative paths, proxied to the backend by Vite in dev
// (see vite.config.ts) and by whatever serves both in production. Set
// VITE_API_BASE to point at a different host entirely if needed.
const BASE = import.meta.env.VITE_API_BASE ?? "";

// The backend has no notion of "the" repository -- every route resolves
// one per-request from a `repo_path` query param (falling back to an env
// var, then cwd, if the param is absent). This module-level variable is
// the frontend's equivalent of a shell's $PWD: whichever repo the user
// last selected, applied to every subsequent call automatically, so
// components don't need to thread a repo path through every prop.
let activeRepoPath: string | null = null;

export function setActiveRepoPath(path: string | null): void {
  activeRepoPath = path && path.trim().length > 0 ? path.trim() : null;
}

export function getActiveRepoPath(): string | null {
  return activeRepoPath;
}

function withRepoParam(path: string): string {
  if (!activeRepoPath) return path;
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}repo_path=${encodeURIComponent(activeRepoPath)}`;
}

export interface Summary {
  worktree: string;
  branch: string;
  head: string | null;
  commit_count: number;
  branch_count: number;
  object_count: number;
  latest_message: string | null;
}

export interface BranchInfo {
  name: string;
  commit: string;
}

export interface BranchList {
  current: string;
  branches: BranchInfo[];
}

export interface CommitSummary {
  hash: string;
  short_hash: string;
  tree: string;
  parents: string[];
  author: string;
  timestamp: number;
  message: string;
}

export interface DiffResult {
  added: string[];
  deleted: string[];
  modified: { path: string; hunks: string[] }[];
}

export interface TreeEntryPayload {
  name: string;
  hash: string;
  type: "blob" | "tree";
  mode: string;
}

export interface TreeObject {
  hash: string;
  entries: TreeEntryPayload[];
}

export type InspectedObject =
  | { type: "commit"; hash: string; tree: string; parents: string[]; author: string; timestamp: number; message: string }
  | { type: "tree"; hash: string; entries: TreeEntryPayload[] }
  | { type: "blob"; hash: string; size: number; binary: boolean; content: string | null };

export interface ApiError {
  error: string;
  message: string;
}

class MiniGitApiError extends Error {
  errorType: string;
  status: number;
  constructor(status: number, body: ApiError) {
    super(body.message);
    this.errorType = body.error;
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${withRepoParam(path)}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({ error: "Unknown", message: res.statusText }))) as ApiError;
    throw new MiniGitApiError(res.status, body);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getSummary: () => request<Summary>("/api/summary"),
  getStatus: () => request<Record<string, unknown>>("/api/status"),
  getBranches: () => request<BranchList>("/api/branches"),
  createBranch: (name: string, startCommit?: string) =>
    request<BranchInfo>("/api/branches", {
      method: "POST",
      body: JSON.stringify({ name, start_commit: startCommit }),
    }),
  getCommits: () => request<CommitSummary[]>("/api/commits"),
  getCommit: (hash: string) => request<CommitSummary>(`/api/commits/${hash}`),
  getCommitDiff: (hash: string) => request<DiffResult>(`/api/commits/${hash}/diff`),
  getObject: (hash: string) => request<InspectedObject>(`/api/objects/${hash}`),
  getTree: (hash: string) => request<TreeObject>(`/api/tree/${hash}`),
  checkout: (branch: string, force = false) =>
    request<{ branch: string; head: string | null }>("/api/checkout", {
      method: "POST",
      body: JSON.stringify({ branch, force }),
    }),
  merge: (branch: string) =>
    request<Record<string, unknown>>("/api/merge", {
      method: "POST",
      body: JSON.stringify({ branch }),
    }),
};

export { MiniGitApiError };
