import { cn, depthLabel } from "@/lib/utils";

const DEPTH_COLORS: Record<number, string> = {
  0: "border-depth-0 text-depth-0",
  1: "border-depth-1 text-depth-1",
  2: "border-depth-2 text-depth-2",
  3: "border-depth-3 text-depth-3",
};

export function DepthBadge({ depth }: { depth: number }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[10px] leading-none",
        DEPTH_COLORS[depth] ?? "border-muted text-muted"
      )}
    >
      {depthLabel(depth)}
    </span>
  );
}
