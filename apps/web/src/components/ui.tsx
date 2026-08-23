import { cn } from "@/lib/utils";

export function Card({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-xl border border-[var(--border)] bg-[var(--panel)] p-5",
        className,
      )}
      {...props}
    />
  );
}

export function Stat({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "warn" | "danger" | "ok";
}) {
  const color =
    tone === "danger"
      ? "text-[var(--danger)]"
      : tone === "warn"
        ? "text-[var(--warn)]"
        : tone === "ok"
          ? "text-[var(--ok)]"
          : "text-[var(--accent)]";
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className={cn("mt-1 text-3xl font-semibold tabular-nums", color)}>{value}</p>
      {hint && <p className="mt-1 text-xs text-[var(--muted)]">{hint}</p>}
    </Card>
  );
}

export function StatusBadge({
  status,
}: {
  status: "live" | "aguardando-dados" | "planejado";
}) {
  const styles = {
    live: "bg-emerald-500/10 text-[var(--ok)]",
    "aguardando-dados": "bg-amber-500/10 text-[var(--warn)]",
    planejado: "bg-slate-500/10 text-[var(--muted)]",
  } as const;
  const dot = {
    live: "bg-[var(--ok)]",
    "aguardando-dados": "bg-[var(--warn)]",
    planejado: "bg-[var(--muted)]",
  } as const;
  const label =
    status === "live"
      ? "dados publicados"
      : status === "planejado"
        ? "planejado"
        : "aguardando pipeline";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        styles[status],
      )}
    >
      <span className={cn("size-1.5 rounded-full", dot[status])} />
      {label}
    </span>
  );
}
