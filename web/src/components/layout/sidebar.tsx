"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Brain, Search, Settings } from "lucide-react";
import { listProjects } from "@/lib/api";
import type { Project } from "@/lib/types";
import { cn } from "@/lib/utils";
import { StatusDot } from "@/components/muninn/status-dot";

const STATUS_ORDER = ["active", "paused", "idea", "archived"] as const;
const STATUS_LABELS: Record<string, string> = {
  active: "Active",
  paused: "Paused",
  idea: "Ideas",
  archived: "Archived",
};

export function Sidebar() {
  const pathname = usePathname();
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => {});
  }, []);

  const grouped = STATUS_ORDER.map((status) => ({
    status,
    label: STATUS_LABELS[status],
    items: projects.filter((p) => p.status === status),
  })).filter((g) => g.items.length > 0);

  return (
    <aside className="flex w-56 flex-col border-r border-border bg-card">
      {/* Logo */}
      <Link
        href="/"
        className="flex items-center gap-2 border-b border-border px-4 py-3"
      >
        <Brain className="h-5 w-5 text-accent" />
        <span className="text-sm font-semibold text-foreground">Muninn</span>
      </Link>

      {/* Nav */}
      <nav className="flex-1 overflow-auto px-2 py-3">
        <Link
          href="/"
          className={cn(
            "flex items-center gap-2 rounded-md px-2 py-1.5 text-xs",
            pathname === "/"
              ? "bg-card-hover text-foreground"
              : "text-muted hover:text-foreground"
          )}
        >
          <Search className="h-3.5 w-3.5" />
          Overview
        </Link>

        {/* Project groups */}
        <div className="mt-4 space-y-4">
          {grouped.map((group) => (
            <div key={group.status}>
              <div className="flex items-center gap-1.5 px-2 pb-1">
                <StatusDot status={group.status} size="sm" />
                <span className="text-[10px] font-medium uppercase tracking-wider text-muted">
                  {group.label}
                </span>
              </div>
              {group.items.map((project) => (
                <Link
                  key={project.id}
                  href={`/projects/${project.id}`}
                  className={cn(
                    "flex items-center justify-between rounded-md px-2 py-1.5 text-xs",
                    pathname === `/projects/${project.id}`
                      ? "bg-card-hover text-foreground"
                      : "text-muted hover:text-foreground"
                  )}
                >
                  <span className="truncate">{project.id}</span>
                  <span className="font-mono text-[10px] text-muted">
                    {project.memory_count}
                  </span>
                </Link>
              ))}
            </div>
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="border-t border-border px-2 py-2">
        <Link
          href="/settings"
          className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-muted hover:text-foreground"
        >
          <Settings className="h-3.5 w-3.5" />
          Settings
        </Link>
      </div>
    </aside>
  );
}
