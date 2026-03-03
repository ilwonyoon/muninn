"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, X } from "lucide-react";
import { listMemories, createMemory } from "@/lib/api";
import type { Memory } from "@/lib/types";
import { cn, getDateGroup } from "@/lib/utils";
import { MarkdownContent } from "@/components/muninn/markdown-content";
import { useAppToast } from "@/lib/toast-context";

interface ProjectProgressViewProps {
  projectId: string;
  onMemoryCreated: () => void;
}

export function ProjectProgressView({ projectId, onMemoryCreated }: ProjectProgressViewProps) {
  const [entries, setEntries] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const { toast } = useAppToast();

  const fetchEntries = useCallback(() => {
    setLoading(true);
    listMemories(projectId, { tags: ["progress"] })
      .then((res) => setEntries(res.memories))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  async function handleSave() {
    if (!draft.trim()) return;
    setSaving(true);
    try {
      await createMemory({
        project_id: projectId,
        content: draft.trim(),
        tags: ["progress"],
        source: "manual",
      });
      setDraft("");
      setAdding(false);
      toast({ title: "Progress saved", variant: "success" });
      fetchEntries();
      onMemoryCreated();
    } catch {
      toast({ title: "Failed to save", variant: "error" });
    } finally {
      setSaving(false);
    }
  }

  function handleCancel() {
    setDraft("");
    setAdding(false);
  }

  if (loading) {
    return (
      <div className="py-8 text-center text-xs text-muted">Loading...</div>
    );
  }

  return (
    <div>
      {/* Add button / inline form */}
      {adding ? (
        <div className="mb-6 rounded-lg border border-border p-4">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="w-full resize-none rounded border border-border bg-background p-3 font-mono text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent min-h-[120px]"
            placeholder="무엇이 달라졌나요? 예: 로그인 화면이 추가되었습니다"
            autoFocus
          />
          <div className="mt-3 flex items-center gap-2">
            <button
              onClick={handleSave}
              disabled={saving || !draft.trim()}
              className="rounded bg-accent px-3 py-1.5 text-xs text-white hover:bg-accent/90 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
            <button
              onClick={handleCancel}
              disabled={saving}
              className="rounded border border-border px-3 py-1.5 text-xs text-muted hover:text-foreground"
            >
              <X className="mr-1 inline h-3 w-3" />
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="mb-6">
          <button
            onClick={() => setAdding(true)}
            className="flex items-center gap-1 rounded border border-border px-2.5 py-1.5 text-xs text-muted hover:text-foreground"
          >
            <Plus className="h-3 w-3" /> Add Progress
          </button>
        </div>
      )}

      {/* Entries */}
      {entries.length === 0 ? (
        <div className="py-12 text-center">
          <p className="text-sm text-muted">
            아직 기록된 진행 사항이 없습니다.
          </p>
          <p className="mt-3 text-xs leading-relaxed text-muted/70">
            이 탭은 프로젝트에서 달라진 점을 기록하는 공간입니다.
            <br />
            예를 들어 &ldquo;로그인 화면이 추가되었습니다&rdquo; 또는
            <br />
            &ldquo;검색 속도가 2배 빨라졌습니다&rdquo; 같은 변화를 남겨보세요.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {entries.map((entry, idx) => {
            const group = getDateGroup(entry.updated_at);
            const prevGroup =
              idx > 0 ? getDateGroup(entries[idx - 1].updated_at) : null;
            const showDivider = group !== prevGroup;

            return (
              <div key={entry.id}>
                {showDivider && (
                  <div className="flex items-center gap-3 py-2 text-[10px] font-medium uppercase tracking-wider text-muted">
                    <div className="h-px flex-1 bg-border" />
                    <span>{group}</span>
                    <div className="h-px flex-1 bg-border" />
                  </div>
                )}
                <div className="rounded-lg border border-border px-4 py-3">
                  <div className="mb-1 flex items-center gap-2 text-[10px] text-muted">
                    <span className="font-mono">{entry.short_id}</span>
                    <span>
                      {new Date(entry.updated_at).toLocaleDateString("ko-KR", {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                  <MarkdownContent content={entry.content} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
