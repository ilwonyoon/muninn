/**
 * Muninn REST API client.
 *
 * In dev mode, Next.js rewrites /api/* → localhost:8000/api/*
 * so all calls go to the relative /api path.
 */

import type {
  DashboardStats,
  MemoriesResponse,
  Memory,
  Project,
  SearchResponse,
} from "./types";

const BASE = "/api";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(body.error ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// -- Projects ---------------------------------------------------------------

export function listProjects(status?: string): Promise<Project[]> {
  const qs = status ? `?status=${status}` : "";
  return fetchJSON(`/projects${qs}`);
}

export function getProject(id: string): Promise<Project> {
  return fetchJSON(`/projects/${id}`);
}

export function createProject(data: {
  id: string;
  name: string;
  summary?: string;
}): Promise<Project> {
  return fetchJSON("/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateProject(
  id: string,
  data: Partial<Pick<Project, "name" | "status" | "summary" | "github_repo">>
): Promise<Project> {
  return fetchJSON(`/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// -- Memories ---------------------------------------------------------------

export function listMemories(
  projectId: string,
  opts?: { maxChars?: number; tags?: string[] }
): Promise<MemoriesResponse> {
  const params = new URLSearchParams();
  if (opts?.maxChars) params.set("max_chars", String(opts.maxChars));
  if (opts?.tags?.length) params.set("tags", opts.tags.join(","));
  const qs = params.toString();
  return fetchJSON(`/projects/${projectId}/memories${qs ? `?${qs}` : ""}`);
}

export function getMemory(id: string): Promise<Memory> {
  return fetchJSON(`/memories/${id}`);
}

export function createMemory(data: {
  project_id: string;
  content: string;
  tags?: string[];
  source?: string;
}): Promise<Memory> {
  return fetchJSON("/memories", {
    method: "POST",
    body: JSON.stringify({ source: "manual", ...data }),
  });
}

export function updateMemory(
  id: string,
  data: Partial<Pick<Memory, "content" | "tags">>
): Promise<Memory> {
  return fetchJSON(`/memories/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteMemory(id: string): Promise<{ deleted: boolean }> {
  return fetchJSON(`/memories/${id}`, { method: "DELETE" });
}

export function getSupersedeChain(id: string): Promise<Memory[]> {
  return fetchJSON(`/memories/${id}/chain`);
}

// -- Search, Tags, Stats ----------------------------------------------------

export function searchMemories(
  query: string,
  opts?: { project?: string; tags?: string[]; limit?: number }
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query });
  if (opts?.project) params.set("project", opts.project);
  if (opts?.tags?.length) params.set("tags", opts.tags.join(","));
  if (opts?.limit) params.set("limit", String(opts.limit));
  return fetchJSON(`/search?${params}`);
}

export function listTags(project?: string): Promise<string[]> {
  const qs = project ? `?project=${project}` : "";
  return fetchJSON(`/tags${qs}`);
}

export function getStats(): Promise<DashboardStats> {
  return fetchJSON("/stats");
}

// -- Summary Revisions -------------------------------------------------------

export function getSummaryRevision(
  projectId: string
): Promise<{ previous_summary: string; updated_at: string } | null> {
  return fetchJSON(`/projects/${projectId}/summary-revision`);
}

export function acknowledgeSummaryRevision(
  projectId: string
): Promise<{ ok: boolean }> {
  return fetchJSON(`/projects/${projectId}/summary-revision/acknowledge`, {
    method: "POST",
  });
}

// -- Instructions ------------------------------------------------------------

export async function getInstructions(): Promise<{ content: string; path: string }> {
  const res = await fetchJSON<{ instructions: string; path: string }>("/instructions");
  return { content: res.instructions, path: res.path };
}

export function updateInstructions(content: string): Promise<{ ok: boolean }> {
  return fetchJSON("/instructions", {
    method: "PUT",
    body: JSON.stringify({ instructions: content }),
  });
}
