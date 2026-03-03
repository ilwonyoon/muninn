"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ChevronRight,
  FileText,
  FolderOpen,
  LayoutDashboard,
  Search,
  Settings,
  User,
} from "lucide-react";
import { RavenIcon } from "@/components/icons/raven-icon";
import { useProjectStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { StatusDot } from "@/components/muninn/status-dot";
import type { Project } from "@/lib/types";

const STATUS_ORDER = ["active", "paused", "idea", "archived"] as const;
const STATUS_LABELS: Record<string, string> = {
  active: "Active",
  paused: "Paused",
  idea: "Ideas",
  archived: "Archived",
};

const CATEGORY_CONFIG = [
  { key: "project" as const, label: "Projects", icon: FolderOpen },
  { key: "personal" as const, label: "Personal", icon: User },
];

function StatusGroup({
  status,
  projects,
  pathname,
}: {
  status: string;
  projects: Project[];
  pathname: string;
}) {
  if (projects.length === 0) return null;
  return (
    <div>
      <div className="flex items-center gap-1.5 px-2 pb-1">
        <StatusDot status={status} size="sm" />
        <span className="text-[10px] font-medium uppercase tracking-wider text-muted">
          {STATUS_LABELS[status]}
        </span>
      </div>
      {projects.map((project) => (
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
  );
}

function CategoryFolder({
  categoryKey,
  label,
  icon: Icon,
  projects,
  pathname,
  defaultOpen,
}: {
  categoryKey: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  projects: Project[];
  pathname: string;
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  const statusGroups = STATUS_ORDER.map((status) => ({
    status,
    items: projects.filter((p) => p.status === status),
  })).filter((g) => g.items.length > 0);

  if (projects.length === 0) return null;

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium text-foreground hover:bg-card-hover"
      >
        <ChevronRight
          className={cn(
            "h-3 w-3 text-muted transition-transform",
            open && "rotate-90"
          )}
        />
        <Icon className="h-3.5 w-3.5 text-muted" />
        <span>{label}</span>
        <span className="ml-auto font-mono text-[10px] text-muted">
          {projects.length}
        </span>
      </button>
      {open && (
        <div className="ml-3 space-y-2 pt-1">
          {statusGroups.map((group) => (
            <StatusGroup
              key={group.status}
              status={group.status}
              projects={group.items}
              pathname={pathname}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { projects, fetchProjects } = useProjectStore();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const projectsByCategory = CATEGORY_CONFIG.map((cat) => ({
    ...cat,
    projects: projects.filter((p) => (p.category ?? "project") === cat.key),
  }));

  return (
    <aside className="flex w-56 flex-col border-r border-border bg-card">
      {/* Logo */}
      <Link
        href="/"
        className="flex items-center gap-2 border-b border-border px-4 py-3"
      >
        <RavenIcon className="h-5 w-5 text-accent" />
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
          <LayoutDashboard className="h-3.5 w-3.5" />
          Overview
        </Link>

        <Link
          href="/search"
          className={cn(
            "flex items-center gap-2 rounded-md px-2 py-1.5 text-xs",
            pathname === "/search"
              ? "bg-card-hover text-foreground"
              : "text-muted hover:text-foreground"
          )}
        >
          <Search className="h-3.5 w-3.5" />
          Search
          <kbd className="ml-auto rounded border border-border px-1 py-0.5 font-mono text-[9px] text-muted">
            Cmd+K
          </kbd>
        </Link>

        {/* Category folders */}
        <div className="mt-4 space-y-2">
          {projectsByCategory.map((cat) => (
            <CategoryFolder
              key={cat.key}
              categoryKey={cat.key}
              label={cat.label}
              icon={cat.icon}
              projects={cat.projects}
              pathname={pathname}
              defaultOpen={cat.key === "project"}
            />
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="border-t border-border px-2 py-2">
        <Link
          href="/instructions"
          className={cn(
            "flex items-center gap-2 rounded-md px-2 py-1.5 text-xs",
            pathname === "/instructions"
              ? "bg-card-hover text-foreground"
              : "text-muted hover:text-foreground"
          )}
        >
          <FileText className="h-3.5 w-3.5" />
          Instructions
        </Link>
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-2 rounded-md px-2 py-1.5 text-xs",
            pathname === "/settings"
              ? "bg-card-hover text-foreground"
              : "text-muted hover:text-foreground"
          )}
        >
          <Settings className="h-3.5 w-3.5" />
          Settings
        </Link>
      </div>
    </aside>
  );
}
