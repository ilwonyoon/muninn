export function TagPill({
  tag,
  onClick,
}: {
  tag: string;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full bg-card-hover px-2 py-0.5 font-mono text-[10px] text-muted transition-colors hover:text-foreground"
    >
      {tag}
    </button>
  );
}
