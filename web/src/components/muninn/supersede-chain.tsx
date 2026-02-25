"use client";

import type { Memory } from "@/lib/types";
import { relativeTime, truncate } from "@/lib/utils";

export function SupersedeChain({ chain }: { chain: Memory[] }) {
  if (chain.length <= 1) return null;

  return (
    <div className="space-y-0">
      {chain.map((mem, i) => {
        const isCurrent = i === 0;
        const isLast = i === chain.length - 1;
        return (
          <div key={mem.id} className="flex gap-3">
            {/* Timeline line + dot */}
            <div className="flex flex-col items-center">
              <div
                className={`h-2.5 w-2.5 shrink-0 rounded-full border-2 ${
                  isCurrent
                    ? "border-accent bg-accent"
                    : mem.superseded_by === "_deleted"
                      ? "border-red-400 bg-transparent"
                      : "border-muted bg-transparent"
                }`}
              />
              {!isLast && (
                <div className="w-px flex-1 bg-border" />
              )}
            </div>

            {/* Content */}
            <div className={`pb-4 ${isCurrent ? "" : "opacity-60"}`}>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] text-muted">
                  {mem.short_id}
                </span>
                {isCurrent && (
                  <span className="rounded bg-accent/10 px-1.5 py-0.5 text-[9px] font-medium text-accent">
                    current
                  </span>
                )}
                {mem.superseded_by === "_deleted" && (
                  <span className="rounded bg-red-500/10 px-1.5 py-0.5 text-[9px] font-medium text-red-400">
                    deleted
                  </span>
                )}
                <span className="text-[10px] text-muted">
                  {relativeTime(mem.created_at)}
                </span>
              </div>
              <div className="mt-0.5 text-xs text-foreground/80">
                {truncate(mem.content, 120)}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
