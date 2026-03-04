"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Plus } from "lucide-react";
import { updateProject } from "@/lib/api";
import type { Project } from "@/lib/types";
import { useProjectMemories } from "@/lib/use-project-memories";
import { cn } from "@/lib/utils";
import { StatusDot } from "@/components/muninn/status-dot";
import { ProjectDocumentView } from "@/components/muninn/project-document-view";
import { ProjectProgressView } from "@/components/muninn/project-progress-view";
import { ProjectTimelineView } from "@/components/muninn/project-timeline-view";
import { MemoryDetailPanel } from "@/components/muninn/memory-detail-panel";
import { SaveMemoryDialog } from "@/components/muninn/save-memory-dialog";
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

  const [panelMemoryId, setPanelMemoryId] = useState<string | null>(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"product" | "progress" | "timeline">("product");

  // Memories sorted by updated_at DESC (already from API)
  const memories = allMemories;

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      switch (e.key) {
        case "n":
          e.preventDefault();
          setSaveOpen(true);
          break;
        case "Escape":
          if (panelMemoryId) {
            setPanelMemoryId(null);
          }
          break;
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [panelMemoryId]);

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
        <div className="mt-6 pl-10">
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
    </div>
  );
}
