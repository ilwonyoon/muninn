/** Mirrors Python Project dataclass. */
export interface Project {
  id: string;
  name: string;
  status: "active" | "paused" | "idea" | "archived";
  summary: string | null;
  github_repo: string | null;
  created_at: string;
  updated_at: string;
  memory_count: number;
  /** Only present on GET /api/projects/:id */
  depth_distribution?: Record<string, number>;
}

/** Mirrors Python Memory dataclass. */
export interface Memory {
  id: string;
  short_id: string;
  project_id: string;
  content: string;
  depth: number;
  depth_label: string;
  source: "conversation" | "github" | "manual";
  tags: string[];
  superseded_by: string | null;
  category: "vision" | "product" | "insight" | "status" | "architecture" | "decision" | "implementation" | "issue";
  parent_memory_id: string | null;
  title: string | null;
  resolved: boolean;
  created_at: string;
  updated_at: string;
}

export interface RecallStats {
  chars_loaded: number;
  chars_budget: number;
  memories_loaded: number;
  memories_dropped: number;
}

export interface MemoriesResponse {
  memories: Memory[];
  stats: RecallStats;
}

export interface SearchResponse {
  results: Memory[];
  count: number;
}

export interface DashboardStats {
  total_projects: number;
  active_projects: number;
  total_memories: number;
  stale_projects: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
}

export interface TreeEdge {
  id: string;
  source: string;
  target: string;
  category: string;
}

export interface MemoryTreeResponse {
  roots: Memory[];
  children: Record<string, Memory[]>;
  edges: TreeEdge[];
}

export interface ApiError {
  error: string;
  code: string;
}
