"use client";

import { useEffect, useState } from "react";
import { Check, CheckCheck, Pencil, X } from "lucide-react";
import { updateProject, getSummaryRevision, acknowledgeSummaryRevision } from "@/lib/api-client";
import type { Project } from "@/lib/types";
import { MarkdownContent } from "@/components/muninn/markdown-content";
import { useAppToast } from "@/lib/toast-context";
import { relativeTime } from "@/lib/utils";
import { getChangedParagraphs } from "@/lib/diff";

interface ProjectDocumentViewProps {
  project: Project;
  onUpdated: () => void;
}

export function ProjectDocumentView({ project, onUpdated }: ProjectDocumentViewProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(project.summary ?? "");
  const [saving, setSaving] = useState(false);
  const [changedParagraphs, setChangedParagraphs] = useState<Set<string> | null>(null);
  const [acknowledging, setAcknowledging] = useState(false);
  const { toast } = useAppToast();

  useEffect(() => {
    if (!project.summary || editing) return;

    let cancelled = false;
    getSummaryRevision(project.id)
      .then((revisions) => {
        if (cancelled) return;
        const latestRevision = revisions[0];
        if (latestRevision && latestRevision.previous_summary) {
          const changed = getChangedParagraphs(project.summary!, latestRevision.previous_summary);
          setChangedParagraphs(changed.size > 0 ? changed : null);
        } else {
          setChangedParagraphs(null);
        }
      })
      .catch(() => {
        if (!cancelled) setChangedParagraphs(null);
      });

    return () => { cancelled = true; };
  }, [project.id, project.summary, editing]);

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

  async function handleAcknowledge() {
    setAcknowledging(true);
    try {
      await acknowledgeSummaryRevision(project.id);
      setChangedParagraphs(null);
    } catch {
      toast({ title: "Failed to acknowledge changes", variant: "error" });
    } finally {
      setAcknowledging(false);
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

  // Split summary into paragraphs for highlight rendering
  const renderContent = () => {
    if (!project.summary) return null;

    if (!changedParagraphs || changedParagraphs.size === 0) {
      return <MarkdownContent content={project.summary} />;
    }

    // Split by double-newline to get paragraphs, render each with potential highlight
    const paragraphs = project.summary
      .split(/\n\n+/)
      .map((p) => p.trim())
      .filter(Boolean);

    return (
      <div>
        {paragraphs.map((para, idx) => {
          const isChanged = changedParagraphs.has(para);
          return isChanged ? (
            <div
              key={idx}
              className="rounded bg-green-900/20 border-l-2 border-green-500 pl-3 -ml-3 mb-1"
            >
              <MarkdownContent content={para} />
            </div>
          ) : (
            <div key={idx}>
              <MarkdownContent content={para} />
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="relative">
      {/* Header: Last updated + action buttons */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {project.updated_at && (
            <span className="text-xs text-muted">
              Last updated: {relativeTime(project.updated_at)}
            </span>
          )}
          {changedParagraphs && changedParagraphs.size > 0 && (
            <button
              onClick={handleAcknowledge}
              disabled={acknowledging}
              className="flex items-center gap-1 rounded border border-green-500/30 bg-green-900/10 px-2 py-1 text-xs text-green-400 hover:bg-green-900/20 disabled:opacity-50"
            >
              <CheckCheck className="h-3 w-3" />
              {acknowledging ? "처리 중…" : "변경 확인 완료"}
            </button>
          )}
        </div>
        <button
          onClick={handleEdit}
          className="rounded p-1.5 text-muted hover:bg-card-hover hover:text-foreground"
          aria-label="Edit document"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
      </div>

      {project.summary ? (
        renderContent()
      ) : (
        <div className="flex flex-col items-center gap-4 py-12">
          <p className="text-sm text-muted">
            아직 작성된 문서가 없습니다.
          </p>
          <p className="text-xs leading-relaxed text-muted/70 text-center">
            이 탭은 프로젝트의 전체 모습을 한 페이지로 정리하는 공간입니다.
            <br />
            프로젝트가 무엇인지, 누구를 위한 것인지, 어떤 방향으로 가고 있는지를
            <br />
            마크다운 문서로 작성해보세요.
          </p>
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
