"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getStats, listProjects } from "@/lib/api";
import type { DashboardStats, Project } from "@/lib/types";
import { relativeTime } from "@/lib/utils";
import { StatCard } from "@/components/muninn/stat-card";
import { StatusDot } from "@/components/muninn/status-dot";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getStats(), listProjects()])
      .then(([s, p]) => {
        setStats(s);
        setProjects(p);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted">
        Loading…
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="text-lg font-semibold text-foreground">Overview</h1>

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
    </div>
  );
}
