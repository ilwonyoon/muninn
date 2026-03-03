"use client";

import { Pencil, Trash2 } from "lucide-react";
import { cn, relativeTime } from "@/lib/utils";
import { TagPill } from "@/components/muninn/tag-pill";
import { MarkdownContent } from "@/components/muninn/markdown-content";

interface MemoryFeedCardProps {
  memory: {
    id: string;
    short_id: string;
    content: string;
    tags: string[];
    updated_at: string;
    superseded_by: string | null;
  };
  selected: boolean;
  active: boolean;
  onSelect: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export function MemoryFeedCard({
  memory,
  selected,
  active,
  onSelect,
  onEdit,
  onDelete,
}: MemoryFeedCardProps) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => e.key === "Enter" && onSelect()}
      className={cn(
        "group cursor-pointer rounded-lg border px-4 py-3 transition-colors hover:bg-card-hover",
        active ? "border-accent bg-card-hover" : "border-border",
        selected && !active && "bg-card-hover",
        memory.superseded_by && "opacity-50",
      )}
    >
      {/* Header: tags left, short_id right */}
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1">
          {memory.tags.map((tag) => (
            <TagPill key={tag} tag={tag} />
          ))}
        </div>
        <span className="shrink-0 font-mono text-[10px] text-muted">
          {memory.short_id}
        </span>
      </div>

      {/* Body: full markdown content */}
      <MarkdownContent content={memory.content} className="text-xs" />

      {/* Footer: timestamp right, action icons on hover */}
      <div className="mt-2 flex items-center justify-end gap-2">
        <span className="text-[10px] text-muted">
          {relativeTime(memory.updated_at)}
        </span>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onEdit();
          }}
          className="opacity-0 transition-opacity group-hover:opacity-100 text-muted hover:text-foreground"
          aria-label="Edit memory"
        >
          <Pencil size={12} />
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="opacity-0 transition-opacity group-hover:opacity-100 text-muted hover:text-red-400"
          aria-label="Delete memory"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );
}
