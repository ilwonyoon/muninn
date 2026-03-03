"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Plus } from "lucide-react";
import { updateProject, deleteMemory } from "@/lib/api";
import type { Memory, Project } from "@/lib/types";
import { useProjectMemories } from "@/lib/use-project-memories";
import { cn, getDateGroup } from "@/lib/utils";
import { StatusDot } from "@/components/muninn/status-dot";
import { MemoryFeedCard } from "@/components/muninn/memory-feed-card";
import { ProjectDocumentView } from "@/components/muninn/project-document-view";
import { ProjectProgressView } from "@/components/muninn/project-progress-view";
import { ProjectTimelineView } from "@/components/muninn/project-timeline-view";
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

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const { toast } = useAppToast();
  const projectId = params.id;

  const { project, allMemories, loading, refetch } =
    useProjectMemories(projectId);

  const [selectedIdx, setSelectedIdx] = useState(-1);
  const [panelMemoryId, setPanelMemoryId] = useState<string | null>(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Memory | null>(null);
  const [deleting, setDeleting] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<"product" | "progress" | "timeline" | "memories">("product");

  // Memories sorted by updated_at DESC (already from API)
  const memories = allMemories;

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
      await updateProject(project.id, { status: next });
      refetch();
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
      refetch();
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
          "flex-1 overflow-y-auto scrollbar-hide px-6 py-8 mx-auto max-w-4xl",
          panelMemoryId && "hidden md:block"
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
          <button
            type="button"
            onClick={() => setSaveOpen(true)}
            className="flex items-center gap-1 rounded border border-border px-2 py-1 text-xs text-muted hover:text-foreground"
            title="New memory (n)"
          >
            <Plus className="h-3 w-3" /> Save
          </button>
        </div>

        {/* Tabs */}
        <div className="mt-6 flex items-center gap-1 border-b border-border pl-10">
          {([
            { key: "product", label: "Product" },
            { key: "progress", label: "Progress" },
            { key: "timeline", label: "Timeline" },
            { key: "memories", label: `Memories (${memories.length})` },
          ] as const).map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                "px-3 py-2 text-xs font-medium transition-colors",
                activeTab === tab.key
                  ? "border-b-2 border-foreground text-foreground"
                  : "text-muted hover:text-foreground"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="mt-6 pl-10" ref={listRef}>
          {activeTab === "product" && (
            <ProjectDocumentView project={project} onUpdated={refetch} />
          )}

          {activeTab === "progress" && (
            <ProjectProgressView projectId={projectId} onMemoryCreated={refetch} />
          )}

          {activeTab === "timeline" && (
            <ProjectTimelineView
              memories={memories}
              onSelectMemory={(shortId) => setPanelMemoryId(shortId)}
            />
          )}

          {activeTab === "memories" && (
            <>
              <div className="space-y-3">
                {memories.length === 0 && (
                  <div className="py-12 text-center">
                    <p className="text-sm text-muted">
                      아직 저장된 메모리가 없습니다.
                    </p>
                    <p className="mt-3 text-xs leading-relaxed text-muted/70">
                      메모리는 프로젝트에 대한 개별 기록입니다.
                      <br />
                      AI와의 대화 중 떠오른 생각, 결정 사항, 방향 전환 등을
                      <br />
                      짧은 메모로 남겨보세요.
                    </p>
                  </div>
                )}
                {memories.map((mem, idx) => {
                  const group = getDateGroup(mem.updated_at);
                  const prevGroup =
                    idx > 0 ? getDateGroup(memories[idx - 1].updated_at) : null;
                  const showDivider = group !== prevGroup;

                  return (
                    <div key={mem.id}>
                      {showDivider && (
                        <div className="flex items-center gap-3 py-2 text-[10px] font-medium uppercase tracking-wider text-muted">
                          <div className="h-px flex-1 bg-border" />
                          <span>{group}</span>
                          <div className="h-px flex-1 bg-border" />
                        </div>
                      )}
                      <MemoryFeedCard
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
                    </div>
                  );
                })}
              </div>

              {/* Keyboard hints */}
              <div className="mt-4 flex items-center gap-3 text-[10px] text-muted">
                <span>
                  <kbd className="rounded border border-border px-1 py-0.5 font-mono">j</kbd>{" "}
                  <kbd className="rounded border border-border px-1 py-0.5 font-mono">k</kbd>{" "}
                  navigate
                </span>
                <span>
                  <kbd className="rounded border border-border px-1 py-0.5 font-mono">Enter</kbd>{" "}
                  open
                </span>
                <span>
                  <kbd className="rounded border border-border px-1 py-0.5 font-mono">n</kbd>{" "}
                  new
                </span>
                <span>
                  <kbd className="rounded border border-border px-1 py-0.5 font-mono">Esc</kbd>{" "}
                  close
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Side panel */}
      {panelMemoryId && (
        <aside className="w-full border-l border-border bg-card animate-slide-in-from-right md:w-[45%] md:min-w-[400px]">
          <MemoryDetailPanel
            memoryId={panelMemoryId}
            projectId={projectId}
            onClose={() => setPanelMemoryId(null)}
            onUpdated={refetch}
            onDeleted={() => {
              setPanelMemoryId(null);
              refetch();
            }}
          />
        </aside>
      )}

      {/* Save dialog */}
      <SaveMemoryDialog
        projectId={projectId}
        open={saveOpen}
        onOpenChange={setSaveOpen}
        onSaved={refetch}
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
