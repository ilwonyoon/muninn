"use client";

import type { Memory } from "@/lib/types";
import { cn, getDateGroup } from "@/lib/utils";

interface ProjectTimelineViewProps {
  memories: Memory[];
  onSelectMemory: (shortId: string) => void;
}

function summarize(content: string, maxLen = 80): string {
  const firstLine = content.split("\n").find((l) => l.trim()) ?? "";
  const clean = firstLine.replace(/^#+\s*/, "").trim();
  if (clean.length <= maxLen) return clean;
  return clean.slice(0, maxLen) + "...";
}

export function ProjectTimelineView({ memories, onSelectMemory }: ProjectTimelineViewProps) {
  if (memories.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-muted">
          아직 기록된 메모리가 없습니다.
        </p>
        <p className="mt-3 text-xs leading-relaxed text-muted/70">
          이 탭은 프로젝트의 모든 기록을 시간순으로 보여줍니다.
          <br />
          AI와의 대화에서 저장된 메모, 직접 작성한 노트,
          <br />
          GitHub 커밋 요약 등이 타임라인에 나타납니다.
        </p>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-[5px] top-0 bottom-0 w-px bg-border" />

      <div className="space-y-0">
        {memories.map((mem, idx) => {
          const group = getDateGroup(mem.updated_at);
          const prevGroup =
            idx > 0 ? getDateGroup(memories[idx - 1].updated_at) : null;
          const showDivider = group !== prevGroup;

          return (
            <div key={mem.id}>
              {showDivider && (
                <div className="relative ml-5 py-2 text-[10px] font-medium uppercase tracking-wider text-muted">
                  {group}
                </div>
              )}
              <button
                type="button"
                onClick={() => onSelectMemory(mem.short_id)}
                className="group flex w-full items-start gap-3 rounded px-0 py-1.5 text-left transition-colors hover:bg-card-hover"
              >
                {/* Dot */}
                <div className="relative mt-1.5 flex-shrink-0">
                  <div
                    className={cn(
                      "h-[11px] w-[11px] rounded-full border-2 border-background",
                      mem.superseded_by
                        ? "bg-muted"
                        : "bg-foreground/60 group-hover:bg-accent"
                    )}
                  />
                </div>

                {/* Content */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 text-[10px] text-muted">
                    <span className="font-mono">{mem.short_id}</span>
                    <span>
                      {new Date(mem.updated_at).toLocaleDateString("ko-KR", {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    {mem.source !== "manual" && (
                      <span className="rounded bg-card-hover px-1 py-0.5 text-[9px]">
                        {mem.source}
                      </span>
                    )}
                  </div>
                  <p
                    className={cn(
                      "mt-0.5 text-sm text-foreground/85",
                      mem.superseded_by && "line-through opacity-50"
                    )}
                  >
                    {summarize(mem.content)}
                  </p>
                  {mem.tags.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {mem.tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded bg-card-hover px-1.5 py-0.5 text-[10px] text-muted"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
