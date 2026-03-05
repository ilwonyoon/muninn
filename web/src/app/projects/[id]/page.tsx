"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Plus } from "lucide-react";
import { updateProject } from "@/lib/api-client";
import type { Project } from "@/lib/types";
import { useProjectMemories } from "@/lib/use-project-memories";
import { cn } from "@/lib/utils";
import { StatusDot } from "@/components/muninn/status-dot";
import { ProjectDocumentView } from "@/components/muninn/project-document-view";
import { ProjectProgressView } from "@/components/muninn/project-progress-view";


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

  const { project, loading, refetch } =
    useProjectMemories(projectId);

  const [saveOpen, setSaveOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"product" | "progress">("product");

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      if (e.key === "n") {
        e.preventDefault();
        setSaveOpen(true);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

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
      <div className="flex-1 overflow-y-auto scrollbar-hide px-6 py-8 mx-auto max-w-4xl">
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
        </div>
      </div>

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
