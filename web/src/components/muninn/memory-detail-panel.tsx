"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Pencil, Trash2, X } from "lucide-react";
import {
  getMemory,
  getSupersedeChain,
  updateMemory,
  deleteMemory,
} from "@/lib/api";
import type { Memory } from "@/lib/types";
import { relativeTime } from "@/lib/utils";
import { TagPill } from "@/components/muninn/tag-pill";
import { MarkdownContent } from "@/components/muninn/markdown-content";
import { SupersedeChain } from "@/components/muninn/supersede-chain";
import { useAppToast } from "@/lib/toast-context";

interface MemoryDetailPanelProps {
  memoryId: string;
  projectId: string;
  onClose: () => void;
  onUpdated: () => void;
  onDeleted: () => void;
}

const SOURCE_ICONS: Record<string, string> = {
  conversation: "\u{1F4AC}",
  github: "\u{1F419}",
  manual: "\u{270F}\u{FE0F}",
};

export function MemoryDetailPanel({
  memoryId,
  projectId,
  onClose,
  onUpdated,
  onDeleted,
}: MemoryDetailPanelProps) {
  const { toast } = useAppToast();

  const [memory, setMemory] = useState<Memory | null>(null);
  const [chain, setChain] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);

  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [editTags, setEditTags] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [mem, ch] = await Promise.all([
        getMemory(memoryId),
        getSupersedeChain(memoryId),
      ]);
      setMemory(mem);
      setChain(ch);
    } catch {
      setMemory(null);
      setChain([]);
    } finally {
      setLoading(false);
    }
  }, [memoryId]);

  useEffect(() => {
    setEditing(false);
    fetchData();
  }, [fetchData]);

  const startEdit = useCallback(() => {
    if (!memory) return;
    setEditContent(memory.content);
    setEditTags(memory.tags.join(", "));
    setEditing(true);
  }, [memory]);

  const cancelEdit = useCallback(() => {
    setEditing(false);
  }, []);

  const saveEdit = useCallback(async () => {
    if (!memory) return;
    setSaving(true);
    try {
      const tags = editTags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      await updateMemory(memory.id, {
        content: editContent,
        tags,
      });
      toast({ title: "Memory updated", variant: "default" });
      setEditing(false);
      await fetchData();
      onUpdated();
    } catch (err) {
      toast({
        title: "Failed to update memory",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "error",
      });
    } finally {
      setSaving(false);
    }
  }, [memory, editContent, editTags, toast, fetchData, onUpdated]);

  const handleDelete = useCallback(async () => {
    if (!memory) return;
    if (!confirm("Delete this memory?")) return;
    try {
      await deleteMemory(memory.id);
      toast({ title: "Memory deleted", variant: "default" });
      onDeleted();
    } catch (err) {
      toast({
        title: "Failed to delete memory",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "error",
      });
    }
  }, [memory, toast, onDeleted]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const inInput =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT";

      if (e.key === "Escape") {
        if (editing) {
          cancelEdit();
        } else {
          onClose();
        }
        return;
      }

      if (e.key === "e" && !editing && !inInput) {
        startEdit();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [editing, cancelEdit, onClose, startEdit]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <span className="text-sm text-muted">Loading...</span>
      </div>
    );
  }

  if (!memory) {
    return (
      <div className="flex h-full items-center justify-center">
        <span className="text-sm text-muted">Memory not found.</span>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm text-muted">{memory.short_id}</span>
        </div>
        <div className="flex items-center gap-1">
          {!editing && (
            <>
              <button
                onClick={startEdit}
                title="Edit (e)"
                className="rounded p-1.5 text-muted hover:bg-card-hover hover:text-foreground"
              >
                <Pencil className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={handleDelete}
                title="Delete"
                className="rounded p-1.5 text-muted hover:bg-card-hover hover:text-red-400"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </>
          )}
          <button
            onClick={onClose}
            title="Close (Esc)"
            className="rounded p-1.5 text-muted hover:bg-card-hover hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {/* Metadata grid */}
        <div className="grid grid-cols-2 gap-y-3 text-sm">
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
          <div>
            <span className="text-muted">Full ID</span>
            <div className="mt-0.5 font-mono text-[10px] text-foreground">
              {memory.id}
            </div>
          </div>
        </div>

        {/* Tags */}
        <div className="mt-4">
          {editing ? (
            <input
              value={editTags}
              onChange={(e) => setEditTags(e.target.value)}
              placeholder="tag1, tag2, ..."
              className="w-full rounded border border-border bg-card px-2 py-1 font-mono text-xs text-foreground placeholder:text-muted"
            />
          ) : (
            <div className="flex flex-wrap gap-1">
              {memory.tags.map((tag) => (
                <TagPill key={tag} tag={tag} />
              ))}
              {memory.tags.length === 0 && (
                <span className="text-[10px] text-muted">no tags</span>
              )}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="mt-6">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted">Content</span>
            {editing && (
              <div className="flex gap-1">
                <button
                  onClick={cancelEdit}
                  disabled={saving}
                  className="flex items-center gap-1 rounded border border-border px-2 py-1 text-xs text-muted hover:text-foreground disabled:opacity-50"
                >
                  <X className="h-3 w-3" />
                  Cancel
                </button>
                <button
                  onClick={saveEdit}
                  disabled={saving}
                  className="flex items-center gap-1 rounded border border-accent bg-accent/10 px-2 py-1 text-xs text-accent hover:bg-accent/20 disabled:opacity-50"
                >
                  <Check className="h-3 w-3" />
                  {saving ? "Saving..." : "Save"}
                </button>
              </div>
            )}
          </div>
          {editing ? (
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              rows={12}
              className="mt-2 w-full resize-y rounded-lg border border-border bg-card-hover p-3 font-mono text-sm leading-relaxed text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
          ) : (
            <div className="mt-2 rounded-lg border border-border bg-card-hover p-4">
              <MarkdownContent content={memory.content} />
            </div>
          )}
        </div>

        {/* Supersede chain */}
        {chain.length > 1 && (
          <div className="mt-8">
            <span className="text-sm font-medium text-muted">
              Version History ({chain.length})
            </span>
            <div className="mt-3">
              <SupersedeChain chain={chain} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
