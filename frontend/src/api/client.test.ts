import { afterEach, describe, expect, it, vi } from "vitest";
import { api, MiniGitApiError, setActiveRepoPath } from "./client";

function mockFetchOnce(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "error",
    json: () => Promise.resolve(body),
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  setActiveRepoPath(null);
});

describe("api client error handling", () => {
  it("resolves normally on a 200", async () => {
    mockFetchOnce(200, { branch: "main", head: "abc123" });
    const result = await api.getStatus();
    expect(result.branch).toBe("main");
  });

  it("throws a typed MiniGitApiError with the backend's error type on failure", async () => {
    mockFetchOnce(404, { error: "BranchNotFound", message: "Branch 'x' not found" });
    await expect(api.getCommit("deadbeef")).rejects.toMatchObject({
      message: "Branch 'x' not found",
      errorType: "BranchNotFound",
      status: 404,
    });
  });

  it("wraps a non-JSON failure response without crashing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: () => Promise.reject(new Error("not json")),
      })
    );
    await expect(api.getBranches()).rejects.toBeInstanceOf(MiniGitApiError);
  });
});

describe("active repo path threading", () => {
  it("does not append a repo_path param when none is set", async () => {
    const fetchMock = mockFetchOnce(200, { current: "main", branches: [] });
    await api.getBranches();
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).not.toContain("repo_path");
  });

  it("appends the active repo path as a query param on every call once set", async () => {
    setActiveRepoPath("/home/user/my-repo");
    const fetchMock = mockFetchOnce(200, { current: "main", branches: [] });
    await api.getBranches();
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain(`repo_path=${encodeURIComponent("/home/user/my-repo")}`);
  });

  it("stops appending it once cleared", async () => {
    setActiveRepoPath("/home/user/my-repo");
    setActiveRepoPath(null);
    const fetchMock = mockFetchOnce(200, { current: "main", branches: [] });
    await api.getBranches();
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).not.toContain("repo_path");
  });

  it("treats an empty/whitespace string the same as clearing it", async () => {
    setActiveRepoPath("   ");
    const fetchMock = mockFetchOnce(200, { current: "main", branches: [] });
    await api.getBranches();
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).not.toContain("repo_path");
  });
});
