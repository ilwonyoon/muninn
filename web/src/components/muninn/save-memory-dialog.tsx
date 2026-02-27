"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { createMemory } from "@/lib/api";
import type { Memory } from "@/lib/types";
import { useAppToast } from "@/lib/toast-context";

export function SaveMemoryDialog({
  projectId,
  open,
  onOpenChange,
  onSaved,
}: {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved?: (memory: Memory) => void;
}) {
  const { toast } = useAppToast();
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!content.trim()) return;
    setSaving(true);
    try {
      const tagList = tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const memory = await createMemory({
        project_id: projectId,
        content: content.trim(),
        tags: tagList.length > 0 ? tagList : undefined,
      });
      toast({ title: "Memory saved", variant: "success" });
      onSaved?.(memory);
      onOpenChange(false);
      // Reset
      setContent("");
      setTags("");
    } catch (err) {
      toast({
        title: "Failed to save",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "error",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogTitle>Save Memory</DialogTitle>
        <DialogDescription>
          Add a new memory to <span className="font-mono">{projectId}</span>
        </DialogDescription>

        <div className="mt-4 space-y-3">
          {/* Content */}
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Memory content..."
            rows={6}
            className="w-full resize-y rounded-md border border-border bg-card-hover p-3 font-mono text-xs text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            autoFocus
          />

          {/* Tags */}
          <div>
            <label className="text-[10px] text-muted">
              Tags (comma-separated)
            </label>
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="decision, architecture, ..."
              className="mt-1 w-full rounded border border-border bg-card px-2 py-1.5 font-mono text-xs text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="rounded border border-border px-3 py-1.5 text-xs text-muted hover:text-foreground"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !content.trim()}
              className="rounded bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-hover disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
