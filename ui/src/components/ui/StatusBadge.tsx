import { cn } from "@/lib/utils";

const badgeClasses: Record<string, string> = {
  sent: "bg-horizon-success/10 text-horizon-success border-horizon-success/20",
  matched: "bg-brand-600/10 text-brand-600 border-brand-600/20",
  completed: "bg-horizon-success/10 text-horizon-success border-horizon-success/20",
  running: "bg-brand-600/10 text-brand-600 border-brand-600/20",
  pending: "bg-horizon-warning/10 text-horizon-warning border-horizon-warning/20",
  skipped_missing_email: "bg-horizon-warning/10 text-horizon-warning border-horizon-warning/20",
  skipped_already_applied: "bg-slate-200 text-slate-700 border-slate-300",
  skipped_startup_already_ran: "bg-slate-200 text-slate-700 border-slate-300",
  skipped_missing_resume: "bg-horizon-danger/10 text-horizon-danger border-horizon-danger/20",
  send_failed: "bg-horizon-danger/10 text-horizon-danger border-horizon-danger/20",
  failed: "bg-horizon-danger/10 text-horizon-danger border-horizon-danger/20"
};

export function StatusBadge({ value }: { value: string }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full border px-3 py-1 text-xs font-semibold capitalize tracking-wide",
        badgeClasses[value] ?? "bg-horizon-info/10 text-horizon-info border-horizon-info/20"
      )}
    >
      {value.split("_").join(" ")}
    </span>
  );
}
