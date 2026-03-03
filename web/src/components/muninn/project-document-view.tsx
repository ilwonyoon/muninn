"use client";

import { useState } from "react";
import { Check, Pencil, X } from "lucide-react";
import { updateProject } from "@/lib/api";
import type { Project } from "@/lib/types";
import { MarkdownContent } from "@/components/muninn/markdown-content";
import { useAppToast } from "@/lib/toast-context";

interface ProjectDocumentViewProps {
  project: Project;
  onUpdated: () => void;
}

export function ProjectDocumentView({ project, onUpdated }: ProjectDocumentViewProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(project.summary ?? "");
  const [saving, setSaving] = useState(false);
  const { toast } = useAppToast();

  function handleEdit() {
    setDraft(project.summary ?? "");
    setEditing(true);
  }

  function handleCancel() {
    setEditing(false);
  }

  async function handleSave() {
    setSaving(true);
    try {
      await updateProject(project.id, { summary: draft });
      onUpdated();
      setEditing(false);
      toast({ title: "Document saved", variant: "success" });
    } catch {
      toast({ title: "Failed to save document", variant: "error" });
    } finally {
      setSaving(false);
    }
  }

  if (editing) {
    return (
      <div className="flex h-full flex-col">
        <div className="mb-3 flex items-center gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded bg-accent px-3 py-1.5 text-xs text-white hover:bg-accent/90 disabled:opacity-50"
          >
            <Check className="mr-1 inline h-3 w-3" />
            {saving ? "Saving…" : "Save"}
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
        <div className="flex flex-1 gap-4 overflow-hidden">
          <div className="flex w-1/2 flex-col">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="w-full flex-1 resize-none rounded border border-border bg-background font-mono text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent min-h-[60vh] p-3"
              placeholder="Write markdown here…"
            />
          </div>
          <div className="w-1/2 overflow-y-auto rounded border border-border bg-card p-4">
            {draft ? (
              <MarkdownContent content={draft} />
            ) : (
              <p className="text-sm text-muted">Preview will appear here.</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={handleEdit}
        className="absolute right-0 top-0 rounded p-1.5 text-muted hover:bg-card-hover hover:text-foreground"
        aria-label="Edit document"
      >
        <Pencil className="h-3.5 w-3.5" />
      </button>

      {project.summary ? (
        <MarkdownContent content={project.summary} />
      ) : (
        <div className="flex flex-col items-start gap-3 py-8">
          <p className="text-sm text-muted">No document yet.</p>
          <button
            onClick={handleEdit}
            className="rounded bg-accent px-3 py-1.5 text-xs text-white hover:bg-accent/90"
          >
            Edit
          </button>
        </div>
      )}
    </div>
  );
}
