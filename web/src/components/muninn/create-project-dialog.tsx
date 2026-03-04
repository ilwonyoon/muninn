"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { createProject } from "@/lib/api-client";
import type { Project } from "@/lib/types";
import { useAppToast } from "@/lib/toast-context";

export function CreateProjectDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: (project: Project) => void;
}) {
  const { toast } = useAppToast();
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [summary, setSummary] = useState("");
  const [saving, setSaving] = useState(false);

  const handleCreate = async () => {
    if (!id.trim() || !name.trim()) return;
    setSaving(true);
    try {
      const project = await createProject({
        id: id.trim(),
        name: name.trim(),
        summary: summary.trim() || undefined,
      });
      toast({ title: "Project created", variant: "success" });
      onCreated?.(project);
      onOpenChange(false);
      setId("");
      setName("");
      setSummary("");
    } catch (err) {
      toast({
        title: "Failed to create",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "error",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogTitle>New Project</DialogTitle>
        <DialogDescription>Create a new project to organize memories.</DialogDescription>

        <div className="mt-4 space-y-3">
          <div>
            <label className="text-[10px] text-muted">ID (slug)</label>
            <input
              value={id}
              onChange={(e) => setId(e.target.value.toLowerCase().replace(/[^a-z0-9-_]/g, ""))}
              placeholder="my-project"
              className="mt-1 w-full rounded border border-border bg-card px-2 py-1.5 font-mono text-xs text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
              autoFocus
            />
          </div>
          <div>
            <label className="text-[10px] text-muted">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Project"
              className="mt-1 w-full rounded border border-border bg-card px-2 py-1.5 text-xs text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </div>
          <div>
            <label className="text-[10px] text-muted">Summary (optional)</label>
            <input
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Brief description..."
              className="mt-1 w-full rounded border border-border bg-card px-2 py-1.5 text-xs text-foreground placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </div>

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
              onClick={handleCreate}
              disabled={saving || !id.trim() || !name.trim()}
              className="rounded bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-hover disabled:opacity-50"
            >
              {saving ? "Creating..." : "Create"}
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
