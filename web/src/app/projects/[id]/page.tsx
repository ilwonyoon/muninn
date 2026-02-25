"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  MoreHorizontal,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react";
import {
  getProject,
  listMemories,
  listTags,
  updateProject,
  deleteMemory,
} from "@/lib/api";
import type { Memory, MemoriesResponse, Project } from "@/lib/types";
import { relativeTime, truncate, cn } from "@/lib/utils";
import { StatusDot } from "@/components/muninn/status-dot";
import { DepthBadge } from "@/components/muninn/depth-badge";
import { TagPill } from "@/components/muninn/tag-pill";
import { SaveMemoryDialog } from "@/components/muninn/save-memory-dialog";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { useAppToast } from "@/lib/toast-context";

const ALL_STATUSES = ["active", "paused", "idea", "archived"] as const;

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { toast } = useAppToast();
  const projectId = params.id;

  const [project, setProject] = useState<Project | null>(null);
  const [data, setData] = useState<MemoriesResponse | null>(null);
  const [allTags, setAllTags] = useState<string[]>([]);
  const [depthFilter, setDepthFilter] = useState<number>(3);
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saveOpen, setSaveOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Memory | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Keyboard navigation
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const listRef = useRef<HTMLDivElement>(null);

  const fetchData = useCallback(() => {
    if (!projectId) return;
    setLoading(true);
    Promise.all([
      getProject(projectId),
      listMemories(projectId, {
        depth: depthFilter,
        tags: tagFilter ? [tagFilter] : undefined,
      }),
      listTags(projectId),
    ])
      .then(([p, m, t]) => {
        setProject(p);
        setData(m);
        setAllTags(t);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId, depthFilter, tagFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const memories = data?.memories ?? [];
  const stats = data?.stats;
  const dist = project?.depth_distribution ?? {};

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
            router.push(
              `/projects/${projectId}/${memories[selectedIdx].short_id}`
            );
          }
          break;
        case "n":
          e.preventDefault();
          setSaveOpen(true);
          break;
        case "d":
          if (selectedIdx >= 0 && memories[selectedIdx]) {
            e.preventDefault();
            setDeleteTarget(memories[selectedIdx]);
          }
          break;
        case "Escape":
          setSelectedIdx(-1);
          break;
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [selectedIdx, memories, projectId, router]); // eslint-disable-line react-hooks/exhaustive-deps

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
    <div className="mx-auto max-w-4xl px-6 py-8">
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
                    <span className="ml-auto text-[10px] text-muted">current</span>
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

      {/* Depth distribution */}
      <div className="mt-6 flex items-center gap-2 pl-10">
        <span className="text-xs text-muted">Depth:</span>
        {[0, 1, 2, 3].map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setDepthFilter(d)}
            className={`rounded border px-2 py-0.5 font-mono text-[10px] transition-colors ${
              depthFilter >= d
                ? "border-foreground/20 text-foreground"
                : "border-border text-muted"
            }`}
          >
            {d} ({dist[String(d)] ?? 0})
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
            className={`rounded-full px-2 py-0.5 text-[10px] ${
              tagFilter === null
                ? "bg-accent text-white"
                : "bg-card-hover text-muted"
            }`}
          >
            all
          </button>
          {allTags.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => setTagFilter(tag === tagFilter ? null : tag)}
              className={`rounded-full px-2 py-0.5 font-mono text-[10px] ${
                tag === tagFilter
                  ? "bg-accent text-white"
                  : "bg-card-hover text-muted hover:text-foreground"
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      )}

      {/* Memory table */}
      <div className="mt-4 pl-10" ref={listRef}>
        <div className="divide-y divide-border rounded-lg border border-border">
          {memories.length === 0 && (
            <div className="px-4 py-6 text-center text-xs text-muted">
              No memories at this depth.
            </div>
          )}
          {memories.map((mem, idx) => (
            <MemoryRow
              key={mem.id}
              memory={mem}
              projectId={projectId}
              selected={selectedIdx === idx}
              onDelete={() => setDeleteTarget(mem)}
            />
          ))}
        </div>

        {/* Budget bar */}
        {stats && (
          <div className="mt-3 flex items-center gap-2 text-[10px] text-muted">
            <div className="h-1.5 flex-1 rounded-full bg-card-hover">
              <div
                className="h-1.5 rounded-full bg-accent"
                style={{
                  width: `${Math.min(
                    100,
                    (stats.chars_loaded / stats.chars_budget) * 100
                  )}%`,
                }}
              />
            </div>
            <span className="font-mono">
              {stats.chars_loaded.toLocaleString()} /{" "}
              {stats.chars_budget.toLocaleString()} chars
            </span>
            {stats.memories_dropped > 0 && (
              <span className="text-status-paused">
                {stats.memories_dropped} dropped
              </span>
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
              d
            </kbd>{" "}
            delete
          </span>
        </div>
      </div>

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

function MemoryRow({
  memory,
  projectId,
  selected,
  onDelete,
}: {
  memory: Memory;
  projectId: string;
  selected: boolean;
  onDelete: () => void;
}) {
  return (
    <div
      className={cn(
        "group flex items-start gap-3 px-4 py-2.5 transition-colors",
        selected && "bg-card-hover"
      )}
    >
      <DepthBadge depth={memory.depth} />
      <Link
        href={`/projects/${projectId}/${memory.short_id}`}
        className="min-w-0 flex-1"
      >
        <div className="text-xs text-foreground">
          {truncate(memory.content, 200)}
        </div>
        {memory.tags.length > 0 && (
          <div className="mt-1 flex gap-1">
            {memory.tags.map((tag) => (
              <TagPill key={tag} tag={tag} />
            ))}
          </div>
        )}
      </Link>
      <div className="flex shrink-0 items-center gap-2">
        <div className="flex flex-col items-end gap-0.5">
          <span className="font-mono text-[10px] text-muted">
            {memory.short_id}
          </span>
          <span className="text-[10px] text-muted">
            {relativeTime(memory.updated_at)}
          </span>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="rounded p-1 text-muted opacity-0 hover:bg-card-hover hover:text-foreground group-hover:opacity-100"
            >
              <MoreHorizontal className="h-3.5 w-3.5" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onSelect={() =>
                window.location.assign(
                  `/projects/${projectId}/${memory.short_id}`
                )
              }
            >
              <Pencil className="h-3 w-3" /> Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem destructive onSelect={onDelete}>
              <Trash2 className="h-3 w-3" /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
