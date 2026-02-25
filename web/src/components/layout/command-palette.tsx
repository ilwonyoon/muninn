"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import {
  Brain,
  FolderPlus,
  Plus,
  Search as SearchIcon,
} from "lucide-react";
import { searchMemories } from "@/lib/api";
import { useProjectStore } from "@/lib/store";
import type { Memory } from "@/lib/types";
import { truncate } from "@/lib/utils";
import { StatusDot } from "@/components/muninn/status-dot";
import { DepthBadge } from "@/components/muninn/depth-badge";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Memory[]>([]);
  const router = useRouter();
  const { projects, fetchProjects } = useProjectStore();

  // Cmd+K toggle
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  // Refresh projects when opened
  useEffect(() => {
    if (open) {
      fetchProjects();
      setQuery("");
      setSearchResults([]);
    }
  }, [open, fetchProjects]);

  // Search as you type (debounced)
  useEffect(() => {
    if (!query.trim() || query.length < 2) {
      setSearchResults([]);
      return;
    }
    const timeout = setTimeout(() => {
      searchMemories(query, { limit: 8 })
        .then((res) => setSearchResults(res.results))
        .catch(() => {});
    }, 200);
    return () => clearTimeout(timeout);
  }, [query]);

  const navigate = useCallback(
    (path: string) => {
      setOpen(false);
      router.push(path);
    },
    [router]
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={() => setOpen(false)}
      />

      {/* Palette */}
      <div className="absolute left-1/2 top-[20%] w-full max-w-lg -translate-x-1/2">
        <Command
          className="overflow-hidden rounded-lg border border-border bg-card shadow-2xl"
          shouldFilter={false}
        >
          <div className="flex items-center border-b border-border px-3">
            <SearchIcon className="mr-2 h-4 w-4 shrink-0 text-muted" />
            <Command.Input
              value={query}
              onValueChange={setQuery}
              placeholder="Search memories, projects..."
              className="flex-1 bg-transparent py-3 text-sm text-foreground outline-none placeholder:text-muted"
            />
            <kbd className="rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-muted">
              ESC
            </kbd>
          </div>

          <Command.List className="max-h-80 overflow-auto p-2">
            <Command.Empty className="py-6 text-center text-xs text-muted">
              No results.
            </Command.Empty>

            {/* Search results */}
            {searchResults.length > 0 && (
              <Command.Group
                heading={
                  <span className="px-2 text-[10px] font-medium uppercase tracking-wider text-muted">
                    Memories
                  </span>
                }
              >
                {searchResults.map((mem) => (
                  <Command.Item
                    key={mem.id}
                    value={`memory-${mem.id}`}
                    onSelect={() =>
                      navigate(
                        `/projects/${mem.project_id}/${mem.short_id}`
                      )
                    }
                    className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-xs text-foreground aria-selected:bg-card-hover"
                  >
                    <DepthBadge depth={mem.depth} />
                    <span className="min-w-0 flex-1 truncate">
                      {truncate(mem.content, 60)}
                    </span>
                    <span className="shrink-0 font-mono text-[10px] text-muted">
                      {mem.project_id}
                    </span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {/* Actions */}
            {!query && (
              <Command.Group
                heading={
                  <span className="px-2 text-[10px] font-medium uppercase tracking-wider text-muted">
                    Actions
                  </span>
                }
              >
                <Command.Item
                  onSelect={() => navigate("/search")}
                  className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-xs text-foreground aria-selected:bg-card-hover"
                >
                  <SearchIcon className="h-3.5 w-3.5 text-muted" />
                  Search all memories
                </Command.Item>
                <Command.Item
                  onSelect={() => navigate("/?action=new-project")}
                  className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-xs text-foreground aria-selected:bg-card-hover"
                >
                  <FolderPlus className="h-3.5 w-3.5 text-muted" />
                  Create new project
                </Command.Item>
              </Command.Group>
            )}

            {/* Projects */}
            {projects.length > 0 && (
              <Command.Group
                heading={
                  <span className="px-2 text-[10px] font-medium uppercase tracking-wider text-muted">
                    Projects
                  </span>
                }
              >
                {projects.map((p) => (
                  <Command.Item
                    key={p.id}
                    value={`project-${p.id}`}
                    onSelect={() => navigate(`/projects/${p.id}`)}
                    className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-xs text-foreground aria-selected:bg-card-hover"
                  >
                    <StatusDot status={p.status} />
                    <span className="flex-1">{p.id}</span>
                    <span className="font-mono text-[10px] text-muted">
                      {p.memory_count}
                    </span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
