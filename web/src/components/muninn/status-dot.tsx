import { cn } from "@/lib/utils";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-status-active",
  paused: "bg-status-paused",
  idea: "bg-status-idea",
  archived: "bg-status-archived",
};

export function StatusDot({
  status,
  size = "md",
}: {
  status: string;
  size?: "sm" | "md";
}) {
  return (
    <span
      className={cn(
        "inline-block shrink-0 rounded-full",
        STATUS_COLORS[status] ?? "bg-muted",
        size === "sm" ? "h-1.5 w-1.5" : "h-2 w-2"
      )}
    />
  );
}
