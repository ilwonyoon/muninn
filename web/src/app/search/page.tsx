"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Search as SearchIcon } from "lucide-react";
import { searchMemories, listTags } from "@/lib/api";
import { useProjectStore } from "@/lib/store";
import type { Memory } from "@/lib/types";
import { truncate, relativeTime } from "@/lib/utils";
import { TagPill } from "@/components/muninn/tag-pill";

export default function SearchPage() {
  return (
    <Suspense>
      <SearchInner />
    </Suspense>
  );
}

function SearchInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialQuery = searchParams.get("q") ?? "";
  const initialProject = searchParams.get("project") ?? "";

  const [query, setQuery] = useState(initialQuery);
  const [projectFilter, setProjectFilter] = useState(initialProject);
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [results, setResults] = useState<Memory[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const { projects, fetchProjects } = useProjectStore();
  const [allTags, setAllTags] = useState<string[]>([]);

  // Load filter options
  useEffect(() => {
    fetchProjects();
    listTags().then(setAllTags).catch(() => {});
  }, [fetchProjects]);

  const doSearch = useCallback(
    async (q: string) => {
      if (!q.trim()) return;
      setLoading(true);
      setSearched(true);
      try {
        const res = await searchMemories(q, {
          project: projectFilter || undefined,
          tags: tagFilter ? [tagFilter] : undefined,
          limit: 50,
        });
        setResults(res.results);
        setCount(res.count);
      } catch {
        setResults([]);
        setCount(0);
      } finally {
        setLoading(false);
      }
    },
    [projectFilter, tagFilter]
  );

  // Auto-search when initial query is provided or filters change
  useEffect(() => {
    if (query.trim()) {
      doSearch(query);
    }
  }, [projectFilter, tagFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    doSearch(query);
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="text-lg font-semibold text-foreground">Search</h1>

      {/* Search form */}
      <form onSubmit={handleSubmit} className="mt-4">
        <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
          <SearchIcon className="h-4 w-4 shrink-0 text-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search memories (FTS5)..."
            className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted"
            autoFocus
          />
          <kbd className="rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-muted">
            Enter
          </kbd>
        </div>
      </form>

      {/* Filters */}
      <div className="mt-3 flex flex-wrap items-center gap-3">
        {/* Project filter */}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-muted">Project:</span>
          <select
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
            className="rounded border border-border bg-card px-2 py-0.5 text-[10px] text-foreground"
          >
            <option value="">all</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.id}
              </option>
            ))}
          </select>
        </div>

        {/* Tag filter */}
        {allTags.length > 0 && (
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-muted">Tag:</span>
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
            {allTags.slice(0, 12).map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() =>
                  setTagFilter(tag === tagFilter ? null : tag)
                }
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
      </div>

      {/* Results */}
      <div className="mt-6">
        {loading && (
          <div className="text-center text-xs text-muted">Searching...</div>
        )}

        {/* Empty state — before any search */}
        {!loading && !searched && (
          <div className="space-y-6">
            {/* Quick search by tag */}
            {allTags.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-muted">Browse by tag</h3>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {allTags.map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => {
                        setQuery(tag);
                        doSearch(tag);
                      }}
                      className="rounded-full bg-card-hover px-2.5 py-1 font-mono text-[11px] text-muted transition-colors hover:text-foreground"
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Project quick links */}
            {projects.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-muted">Projects</h3>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {projects.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => {
                        setProjectFilter(p.id);
                        if (query.trim()) doSearch(query);
                      }}
                      className="rounded border border-border px-2.5 py-1 text-[11px] text-muted transition-colors hover:text-foreground"
                    >
                      {p.id}
                      <span className="ml-1 font-mono text-[10px] text-muted/60">
                        {p.memory_count}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Tips */}
            <div className="rounded-lg border border-border bg-card p-4 text-xs text-muted">
              <p className="font-medium text-foreground">Search tips</p>
              <ul className="mt-2 space-y-1">
                <li>FTS5 supports prefix matching: <code className="font-mono text-foreground">auth*</code></li>
                <li>Combine with project/tag filters to narrow results</li>
                <li>Use <kbd className="rounded border border-border px-1 py-0.5 font-mono text-[10px]">Cmd+K</kbd> for quick search anywhere</li>
              </ul>
            </div>
          </div>
        )}

        {!loading && searched && results.length === 0 && (
          <div className="text-center text-xs text-muted">
            No results for &ldquo;{query}&rdquo;
          </div>
        )}

        {!loading && results.length > 0 && (
          <>
            <div className="mb-3 text-[10px] text-muted">
              {count} result{count !== 1 && "s"}
            </div>
            <div className="divide-y divide-border rounded-lg border border-border">
              {results.map((mem) => (
                <Link
                  key={mem.id}
                  href={`/projects/${mem.project_id}/${mem.short_id}`}
                  className="flex items-start gap-3 px-4 py-3 transition-colors hover:bg-card-hover"
                >
                  <span className="shrink-0 rounded bg-card-hover px-1.5 py-0.5 font-mono text-[10px] text-muted">
                    {mem.short_id}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-xs text-foreground">
                      {truncate(mem.content, 200)}
                    </div>
                    <div className="mt-1 flex items-center gap-2">
                      <span className="font-mono text-[10px] text-muted">
                        {mem.project_id}
                      </span>
                      {mem.tags.map((tag) => (
                        <TagPill key={tag} tag={tag} />
                      ))}
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-0.5">
                    <span className="font-mono text-[10px] text-muted">
                      {mem.short_id}
                    </span>
                    <span className="text-[10px] text-muted">
                      {relativeTime(mem.updated_at)}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
