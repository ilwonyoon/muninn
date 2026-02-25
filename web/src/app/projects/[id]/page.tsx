"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getProject, listMemories, listTags } from "@/lib/api";
import type { Memory, MemoriesResponse, Project } from "@/lib/types";
import { relativeTime, truncate } from "@/lib/utils";
import { StatusDot } from "@/components/muninn/status-dot";
import { DepthBadge } from "@/components/muninn/depth-badge";
import { TagPill } from "@/components/muninn/tag-pill";

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;

  const [project, setProject] = useState<Project | null>(null);
  const [data, setData] = useState<MemoriesResponse | null>(null);
  const [allTags, setAllTags] = useState<string[]>([]);
  const [depthFilter, setDepthFilter] = useState<number>(3);
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch project + memories
  useEffect(() => {
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

  if (loading && !project) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted">
        Loading…
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

  const memories = data?.memories ?? [];
  const stats = data?.stats;
  const dist = project.depth_distribution ?? {};

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/" className="text-muted hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <StatusDot status={project.status} />
        <h1 className="text-lg font-semibold text-foreground">{project.id}</h1>
        <span className="text-xs text-muted">{project.status}</span>
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
      <div className="mt-4 pl-10">
        <div className="divide-y divide-border rounded-lg border border-border">
          {memories.length === 0 && (
            <div className="px-4 py-6 text-center text-xs text-muted">
              No memories at this depth.
            </div>
          )}
          {memories.map((mem) => (
            <MemoryRow key={mem.id} memory={mem} />
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
      </div>
    </div>
  );
}

function MemoryRow({ memory }: { memory: Memory }) {
  return (
    <div className="flex items-start gap-3 px-4 py-2.5">
      <DepthBadge depth={memory.depth} />
      <div className="min-w-0 flex-1">
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
      </div>
      <div className="flex shrink-0 flex-col items-end gap-0.5">
        <span className="font-mono text-[10px] text-muted">
          {memory.short_id}
        </span>
        <span className="text-[10px] text-muted">
          {relativeTime(memory.updated_at)}
        </span>
      </div>
    </div>
  );
}
