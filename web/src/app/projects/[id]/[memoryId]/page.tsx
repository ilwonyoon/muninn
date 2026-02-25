"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Check,
  Pencil,
  Trash2,
  X,
} from "lucide-react";
import {
  getMemory,
  getSupersedeChain,
  updateMemory,
  deleteMemory,
} from "@/lib/api";
import type { Memory } from "@/lib/types";
import { relativeTime } from "@/lib/utils";
import { DepthBadge } from "@/components/muninn/depth-badge";
import { TagPill } from "@/components/muninn/tag-pill";
import { SupersedeChain } from "@/components/muninn/supersede-chain";
import { useAppToast } from "@/lib/toast-context";

const SOURCE_ICONS: Record<string, string> = {
  conversation: "\u{1F4AC}",
  github: "\u{1F419}",
  manual: "\u{270F}\u{FE0F}",
};

export default function MemoryDetailPage() {
  const params = useParams<{ id: string; memoryId: string }>();
  const router = useRouter();
  const { toast } = useAppToast();

  const [memory, setMemory] = useState<Memory | null>(null);
  const [chain, setChain] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);

  // Edit state
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [editDepth, setEditDepth] = useState(1);
  const [editTags, setEditTags] = useState("");
  const [saving, setSaving] = useState(false);

  const projectId = params.id;
  const memoryId = params.memoryId;

  const fetchData = useCallback(() => {
    if (!memoryId) return;
    setLoading(true);
    Promise.all([getMemory(memoryId), getSupersedeChain(memoryId)])
      .then(([m, c]) => {
        setMemory(m);
        setChain(c);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [memoryId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const startEdit = () => {
    if (!memory) return;
    setEditContent(memory.content);
    setEditDepth(memory.depth);
    setEditTags(memory.tags.join(", "));
    setEditing(true);
  };

  const cancelEdit = () => {
    setEditing(false);
  };

  const saveEdit = async () => {
    if (!memory) return;
    setSaving(true);
    try {
      const tags = editTags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const updated = await updateMemory(memory.id, {
        content: editContent,
        depth: editDepth,
        tags,
      });
      setMemory(updated);
      setEditing(false);
      toast({ title: "Memory updated", variant: "success" });
    } catch (err) {
      toast({
        title: "Failed to update",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "error",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!memory) return;
    if (!confirm("Delete this memory?")) return;
    try {
      await deleteMemory(memory.id);
      toast({ title: "Memory deleted", variant: "success" });
      router.push(`/projects/${projectId}`);
    } catch (err) {
      toast({
        title: "Failed to delete",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "error",
      });
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted">
        Loading...
      </div>
    );
  }

  if (!memory) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted">
        Memory not found.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      {/* Breadcrumb + actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Link
            href={`/projects/${projectId}`}
            className="text-muted hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <span className="text-xs text-muted">{projectId}</span>
          <span className="text-xs text-muted">/</span>
          <span className="font-mono text-xs text-foreground">
            {memory.short_id}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {!editing && (
            <>
              <button
                type="button"
                onClick={startEdit}
                className="rounded p-1.5 text-muted hover:bg-card-hover hover:text-foreground"
                title="Edit (e)"
              >
                <Pencil className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={handleDelete}
                className="rounded p-1.5 text-muted hover:bg-card-hover hover:text-red-400"
                title="Delete (d)"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Metadata */}
      <div className="mt-4 grid grid-cols-2 gap-y-2 text-xs">
        <div>
          <span className="text-muted">ID</span>
          <div className="mt-0.5 font-mono text-foreground">{memory.id}</div>
        </div>
        <div>
          <span className="text-muted">Source</span>
          <div className="mt-0.5 text-foreground">
            {SOURCE_ICONS[memory.source] ?? ""} {memory.source}
          </div>
        </div>
        <div>
          <span className="text-muted">Created</span>
          <div className="mt-0.5 text-foreground">
            {relativeTime(memory.created_at)}
          </div>
        </div>
        <div>
          <span className="text-muted">Updated</span>
          <div className="mt-0.5 text-foreground">
            {relativeTime(memory.updated_at)}
          </div>
        </div>
      </div>

      {/* Depth + tags */}
      <div className="mt-4 flex items-center gap-3">
        {editing ? (
          <select
            value={editDepth}
            onChange={(e) => setEditDepth(Number(e.target.value))}
            className="rounded border border-border bg-card px-2 py-1 font-mono text-[10px] text-foreground"
          >
            <option value={0}>0 - summary</option>
            <option value={1}>1 - context</option>
            <option value={2}>2 - detailed</option>
            <option value={3}>3 - full</option>
          </select>
        ) : (
          <DepthBadge depth={memory.depth} />
        )}
        {editing ? (
          <input
            value={editTags}
            onChange={(e) => setEditTags(e.target.value)}
            placeholder="tag1, tag2, ..."
            className="flex-1 rounded border border-border bg-card px-2 py-1 font-mono text-[10px] text-foreground placeholder:text-muted"
          />
        ) : (
          <div className="flex flex-wrap gap-1">
            {memory.tags.map((tag) => (
              <TagPill key={tag} tag={tag} />
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="mt-6">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted">Content</span>
          {editing && (
            <div className="flex gap-1">
              <button
                type="button"
                onClick={cancelEdit}
                disabled={saving}
                className="flex items-center gap-1 rounded border border-border px-2 py-1 text-[10px] text-muted hover:text-foreground"
              >
                <X className="h-3 w-3" /> Cancel
              </button>
              <button
                type="button"
                onClick={saveEdit}
                disabled={saving}
                className="flex items-center gap-1 rounded border border-accent bg-accent/10 px-2 py-1 text-[10px] text-accent hover:bg-accent/20"
              >
                <Check className="h-3 w-3" /> {saving ? "Saving..." : "Save"}
              </button>
            </div>
          )}
        </div>
        {editing ? (
          <textarea
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            rows={12}
            className="mt-2 w-full resize-y rounded-lg border border-border bg-card-hover p-3 font-mono text-xs text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
          />
        ) : (
          <div className="mt-2 whitespace-pre-wrap rounded-lg border border-border bg-card-hover p-4 font-mono text-xs leading-relaxed text-foreground">
            {memory.content}
          </div>
        )}
      </div>

      {/* Supersede chain */}
      {chain.length > 1 && (
        <div className="mt-8">
          <span className="text-xs font-medium text-muted">
            Version History ({chain.length})
          </span>
          <div className="mt-3">
            <SupersedeChain chain={chain} />
          </div>
        </div>
      )}
    </div>
  );
}
