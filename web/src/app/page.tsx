"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { FolderPlus } from "lucide-react";
import { getStats } from "@/lib/api-client";
import { useProjectStore } from "@/lib/store";
import type { DashboardStats } from "@/lib/types";
import { relativeTime } from "@/lib/utils";
import { StatCard } from "@/components/muninn/stat-card";
import { StatusDot } from "@/components/muninn/status-dot";
import { CreateProjectDialog } from "@/components/muninn/create-project-dialog";

export default function DashboardPage() {
  return (
    <Suspense>
      <DashboardInner />
    </Suspense>
  );
}

function DashboardInner() {
  const searchParams = useSearchParams();
  const { projects, fetchProjects } = useProjectStore();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);

  const fetchData = () => {
    Promise.all([getStats(), fetchProjects()])
      .then(([s]) => setStats(s))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Open create dialog if navigated via ?action=new-project
  useEffect(() => {
    if (searchParams.get("action") === "new-project") {
      setCreateOpen(true);
    }
  }, [searchParams]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted">
        Loading...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-foreground">Overview</h1>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          className="flex items-center gap-1 rounded border border-border px-2 py-1 text-xs text-muted hover:text-foreground"
        >
          <FolderPlus className="h-3 w-3" /> New Project
        </button>
      </div>

      {/* Stat cards */}
      {stats && (
        <div className="mt-4 grid grid-cols-4 gap-3">
          <StatCard label="total memories" value={stats.total_memories} />
          <StatCard label="projects" value={stats.total_projects} />
          <StatCard label="active" value={stats.active_projects} />
          <StatCard label="stale" value={stats.stale_projects} />
        </div>
      )}

      {/* Project list */}
      <div className="mt-8">
        <h2 className="text-sm font-medium text-muted">Projects</h2>
        <div className="mt-2 divide-y divide-border rounded-lg border border-border">
          {projects.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-muted">
              No projects yet.
            </div>
          )}
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-card-hover"
            >
              <StatusDot status={project.status} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-foreground">
                    {project.id}
                  </span>
                  {project.name !== project.id && (
                    <span className="text-xs text-muted">{project.name}</span>
                  )}
                </div>
                {project.summary && (
                  <div className="truncate text-xs text-muted">
                    {project.summary}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-4 text-xs text-muted">
                <span className="font-mono">
                  {project.memory_count} memories
                </span>
                <span>{relativeTime(project.updated_at)}</span>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Cmd+K hint */}
      <div className="mt-6 text-center text-[10px] text-muted">
        Press{" "}
        <kbd className="rounded border border-border px-1 py-0.5 font-mono">
          Cmd+K
        </kbd>{" "}
        to search
      </div>

      <CreateProjectDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={() => fetchData()}
      />
    </div>
  );
}
