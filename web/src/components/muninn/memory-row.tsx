"use client";

import { Trash2, Pencil } from "lucide-react";
import { TagPill } from "@/components/muninn/tag-pill";
import { cn, extractTitle, extractBody, relativeTime } from "@/lib/utils";

interface MemoryRowProps {
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

export function MemoryRow({
  memory,
  selected,
  active,
  onSelect,
  onEdit,
  onDelete,
}: MemoryRowProps) {
  const title = extractTitle(memory.content);
  const body = extractBody(memory.content);

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit();
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete();
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => e.key === "Enter" && onSelect()}
      className={cn(
        "group cursor-pointer px-4 py-3 transition-colors",
        "hover:bg-card-hover",
        selected && "bg-card-hover",
        active && "border-l-2 border-l-accent bg-card-hover",
        !active && "border-l-2 border-l-transparent",
        memory.superseded_by && "opacity-50"
      )}
    >
      {/* Title */}
      <p className="text-xs font-medium leading-snug text-foreground">
        {title}
      </p>

      {/* Body preview */}
      {body && (
        <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted">
          {body}
        </p>
      )}

      {/* Bottom row: tags + time + short_id + actions */}
      <div className="mt-2 flex items-center gap-2">
        {memory.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {memory.tags.map((tag) => (
              <TagPill key={tag} tag={tag} />
            ))}
          </div>
        )}
        <span className="ml-auto flex items-center gap-2 font-mono text-[10px] text-muted">
          <span>{relativeTime(memory.updated_at)}</span>
          <span>{memory.short_id}</span>
        </span>
        <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            type="button"
            onClick={handleEdit}
            title="Edit"
            className="rounded p-0.5 text-muted hover:text-foreground"
          >
            <Pencil size={11} />
          </button>
          <button
            type="button"
            onClick={handleDelete}
            title="Delete"
            className="rounded p-0.5 text-muted hover:text-red-400"
          >
            <Trash2 size={11} />
          </button>
        </div>
      </div>
    </div>
  );
}
