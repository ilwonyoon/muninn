"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Plus, List, Network } from "lucide-react";
import {
  getProject,
  listMemories,
  listTags,
  updateProject,
  deleteMemory,
  getMemoryTree,
} from "@/lib/api";
import type { Memory, MemoriesResponse, Project, MemoryTreeResponse } from "@/lib/types";
import { MemoryGraphView } from "@/components/muninn/memory-graph-view";
import { cn } from "@/lib/utils";
import { StatusDot } from "@/components/muninn/status-dot";
import { MemoryRow } from "@/components/muninn/memory-row";
import { MemoryDetailPanel } from "@/components/muninn/memory-detail-panel";
import { SaveMemoryDialog } from "@/components/muninn/save-memory-dialog";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { useAppToast } from "@/lib/toast-context";

const ALL_STATUSES = ["active", "paused", "idea", "archived"] as const;

const DEPTH_LABELS: Record<number, string> = {
  0: "summary",
  1: "context",
  2: "detailed",
  3: "full",
};

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const { toast } = useAppToast();
  const projectId = params.id;

  const [project, setProject] = useState<Project | null>(null);
  const [data, setData] = useState<MemoriesResponse | null>(null);
  const [allTags, setAllTags] = useState<string[]>([]);
  const [depthFilter, setDepthFilter] = useState<number | null>(null);
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saveOpen, setSaveOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Memory | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Panel + selection state
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const [panelMemoryId, setPanelMemoryId] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const [viewMode, setViewMode] = useState<"list" | "graph">("list");
  const [graphData, setGraphData] = useState<MemoryTreeResponse | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);

  // Always fetch all memories (depth=3 gets everything)
  const fetchData = useCallback(() => {
    if (!projectId) return;
    setLoading(true);
    Promise.all([
      getProject(projectId),
      listMemories(projectId, { depth: 3 }),
      listTags(projectId),
    ])
      .then(([p, m, t]) => {
        setProject(p);
        setData(m);
        setAllTags(t);
        setGraphData(null);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Lazy-fetch graph data when switching to graph view
  useEffect(() => {
    if (viewMode !== "graph" || !projectId) return;
    if (graphData) return; // already loaded
    setGraphLoading(true);
    getMemoryTree(projectId)
      .then(setGraphData)
      .catch(() => {})
      .finally(() => setGraphLoading(false));
  }, [viewMode, projectId, graphData]);

  // Client-side filtering: exact depth match + tag
  const allMemories = data?.memories ?? [];
  const stats = data?.stats;
  const dist = project?.depth_distribution ?? {};

  const memories = allMemories.filter((m) => {
    if (depthFilter !== null && m.depth !== depthFilter) return false;
    if (tagFilter && !m.tags.includes(tagFilter)) return false;
    return true;
  });

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      switch (e.key) {
        case "j":
          e.preventDefault();
          setSelectedIdx((i) => Math.min(i + 1, memories.length - 1));
          break;
        case "k":
          e.preventDefault();
          setSelectedIdx((i) => Math.max(i - 1, 0));
          break;
        case "Enter":
          if (selectedIdx >= 0 && memories[selectedIdx]) {
            e.preventDefault();
            setPanelMemoryId(memories[selectedIdx].short_id);
          }
          break;
        case "n":
          e.preventDefault();
          setSaveOpen(true);
          break;
        case "Escape":
          if (panelMemoryId) {
            setPanelMemoryId(null);
          } else {
            setSelectedIdx(-1);
          }
          break;
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [selectedIdx, memories, panelMemoryId]);

  const handleStatusChange = async (next: Project["status"]) => {
    if (!project || next === project.status) return;
    try {
      const updated = await updateProject(project.id, { status: next });
      setProject(updated);
      toast({ title: `Status: ${next}`, variant: "success" });
    } catch (err) {
      toast({
        title: "Failed to update status",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "error",
      });
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteMemory(deleteTarget.id);
      toast({ title: "Memory deleted", variant: "success" });
      setDeleteTarget(null);
      if (panelMemoryId === deleteTarget.short_id) {
        setPanelMemoryId(null);
      }
      fetchData();
    } catch (err) {
      toast({
        title: "Failed to delete",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "error",
      });
    } finally {
      setDeleting(false);
    }
  };

  if (loading && !project) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted">
        Loading...
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted">
        Project not found.
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Main list pane */}
      <div
        className={cn(
          "flex-1 overflow-y-auto px-6 py-8",
          panelMemoryId
            ? "hidden md:block"
            : viewMode === "list"
              ? "mx-auto max-w-4xl"
              : ""
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-muted hover:text-foreground">
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="flex items-center gap-1.5 rounded px-1.5 py-0.5 text-xs text-muted hover:bg-card-hover hover:text-foreground"
                >
                  <StatusDot status={project.status} />
                  <span>{project.status}</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                {ALL_STATUSES.map((s) => (
                  <DropdownMenuItem
                    key={s}
                    onSelect={() => handleStatusChange(s)}
                    className={cn(s === project.status && "font-medium")}
                  >
                    <StatusDot status={s} />
                    <span className="capitalize">{s}</span>
                    {s === project.status && (
                      <span className="ml-auto text-[10px] text-muted">
                        current
                      </span>
                    )}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
            <h1 className="text-lg font-semibold text-foreground">
              {project.id}
            </h1>
          </div>
          <div className="flex items-center gap-1">
            {/* View toggle */}
            <div className="flex items-center rounded border border-border">
              <button
                type="button"
                onClick={() => setViewMode("list")}
                className={cn(
                  "rounded-l px-2 py-1 text-xs transition-colors",
                  viewMode === "list"
                    ? "bg-card-hover text-foreground"
                    : "text-muted hover:text-foreground"
                )}
                title="List view"
              >
                <List className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode("graph")}
                className={cn(
                  "rounded-r px-2 py-1 text-xs transition-colors",
                  viewMode === "graph"
                    ? "bg-card-hover text-foreground"
                    : "text-muted hover:text-foreground"
                )}
                title="Graph view"
              >
                <Network className="h-3.5 w-3.5" />
              </button>
            </div>
            <button
              type="button"
              onClick={() => setSaveOpen(true)}
              className="flex items-center gap-1 rounded border border-border px-2 py-1 text-xs text-muted hover:text-foreground"
              title="New memory (n)"
            >
              <Plus className="h-3 w-3" /> Save
            </button>
          </div>
        </div>
        {project.summary && (
          <p className="mt-1 pl-10 text-xs text-muted">{project.summary}</p>
        )}
        {project.github_repo && (
          <p className="mt-0.5 pl-10 font-mono text-[10px] text-muted">
            {project.github_repo}
          </p>
        )}

        {viewMode === "list" ? (
          <>
            {/* Depth tabs — exclusive filter */}
            <div className="mt-6 flex items-center gap-2 overflow-x-auto pl-10">
              <span className="text-xs text-muted">Depth:</span>
              <button
                type="button"
                onClick={() => setDepthFilter(null)}
                className={cn(
                  "rounded border px-2 py-0.5 font-mono text-[10px] transition-colors",
                  depthFilter === null
                    ? "border-foreground/20 text-foreground"
                    : "border-border text-muted hover:text-foreground"
                )}
              >
                All ({allMemories.length})
              </button>
              {[0, 1, 2, 3].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDepthFilter(depthFilter === d ? null : d)}
                  className={cn(
                    "rounded border px-2 py-0.5 font-mono text-[10px] transition-colors",
                    depthFilter === d
                      ? "border-foreground/20 text-foreground"
                      : "border-border text-muted hover:text-foreground"
                  )}
                >
                  {d} {DEPTH_LABELS[d]} ({dist[String(d)] ?? 0})
                </button>
              ))}
            </div>

            {/* Tag filter */}
            {allTags.length > 0 && (
              <div className="mt-2 flex flex-wrap items-center gap-1 pl-10">
                <span className="text-xs text-muted">Tags:</span>
                <button
                  type="button"
                  onClick={() => setTagFilter(null)}
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[10px]",
                    tagFilter === null
                      ? "bg-accent text-white"
                      : "bg-card-hover text-muted"
                  )}
                >
                  all
                </button>
                {allTags.map((tag) => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => setTagFilter(tag === tagFilter ? null : tag)}
                    className={cn(
                      "rounded-full px-2 py-0.5 font-mono text-[10px]",
                      tag === tagFilter
                        ? "bg-accent text-white"
                        : "bg-card-hover text-muted hover:text-foreground"
                    )}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            )}

            {/* Memory list */}
            <div className="mt-4 pl-10" ref={listRef}>
              <div className="divide-y divide-border rounded-lg border border-border">
                {memories.length === 0 && (
                  <div className="px-4 py-6 text-center text-xs text-muted">
                    {depthFilter !== null
                      ? `No memories at depth ${depthFilter}.`
                      : "No memories yet."}
                  </div>
                )}
                {memories.map((mem, idx) => (
                  <MemoryRow
                    key={mem.id}
                    memory={mem}
                    selected={selectedIdx === idx}
                    active={panelMemoryId === mem.short_id}
                    onSelect={() => {
                      setSelectedIdx(idx);
                      setPanelMemoryId(mem.short_id);
                    }}
                    onEdit={() => {
                      setPanelMemoryId(mem.short_id);
                    }}
                    onDelete={() => setDeleteTarget(mem)}
                  />
                ))}
              </div>

              {/* Budget stat — text only, not a slider */}
              {stats && (
                <div className="mt-3 flex items-center gap-3 text-[10px] text-muted">
                  <span className="font-mono">
                    {stats.chars_loaded.toLocaleString()} chars loaded
                  </span>
                  <span className="text-border">|</span>
                  <span className="font-mono">
                    {stats.chars_budget.toLocaleString()} budget
                  </span>
                  {stats.memories_dropped > 0 && (
                    <>
                      <span className="text-border">|</span>
                      <span className="font-mono text-status-paused">
                        {stats.memories_dropped} dropped
                      </span>
                    </>
                  )}
                </div>
              )}

              {/* Keyboard hints */}
              <div className="mt-4 flex items-center gap-3 text-[10px] text-muted">
                <span>
                  <kbd className="rounded border border-border px-1 py-0.5 font-mono">
                    j
                  </kbd>{" "}
                  <kbd className="rounded border border-border px-1 py-0.5 font-mono">
                    k
                  </kbd>{" "}
                  navigate
                </span>
                <span>
                  <kbd className="rounded border border-border px-1 py-0.5 font-mono">
                    Enter
                  </kbd>{" "}
                  open
                </span>
                <span>
                  <kbd className="rounded border border-border px-1 py-0.5 font-mono">
                    n
                  </kbd>{" "}
                  new
                </span>
                <span>
                  <kbd className="rounded border border-border px-1 py-0.5 font-mono">
                    Esc
                  </kbd>{" "}
                  close
                </span>
              </div>
            </div>
          </>
        ) : (
          /* Graph view */
          <div className="mt-6 h-[calc(100vh-140px)]">
            {graphLoading ? (
              <div className="flex h-full items-center justify-center text-sm text-muted">
                Loading graph...
              </div>
            ) : graphData ? (
              <MemoryGraphView
                treeData={graphData}
                activeMemoryId={panelMemoryId}
                onNodeSelect={(shortId) => setPanelMemoryId(shortId)}
                onDeleteRequest={(mem) => setDeleteTarget(mem)}
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-muted">
                No graph data available.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Side panel */}
      {panelMemoryId && (
        <aside className="w-full border-l border-border bg-card animate-slide-in-from-right md:w-[45%] md:min-w-[400px]">
          <MemoryDetailPanel
            memoryId={panelMemoryId}
            projectId={projectId}
            onClose={() => setPanelMemoryId(null)}
            onUpdated={fetchData}
            onDeleted={() => {
              setPanelMemoryId(null);
              fetchData();
            }}
          />
        </aside>
      )}

      {/* Save dialog */}
      <SaveMemoryDialog
        projectId={projectId}
        open={saveOpen}
        onOpenChange={setSaveOpen}
        onSaved={() => fetchData()}
      />

      {/* Delete confirmation */}
      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title={`Delete memory ${deleteTarget?.short_id ?? ""}?`}
        description="This action cannot be undone."
        preview={deleteTarget?.content}
        confirmLabel="Delete"
        destructive
        loading={deleting}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
