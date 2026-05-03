import type { ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: number | string;
  caption: string;
  icon: ReactNode;
  tone: "brand" | "success" | "warning" | "danger" | "info";
}

const toneMap = {
  brand: "bg-brand-600 text-white shadow-soft",
  success: "bg-horizon-success text-white shadow-[0_10px_22px_rgba(5,205,153,0.18)]",
  warning: "bg-horizon-warning text-white shadow-[0_10px_22px_rgba(255,181,71,0.18)]",
  danger: "bg-horizon-danger text-white shadow-[0_10px_22px_rgba(238,93,80,0.18)]",
  info: "bg-horizon-info text-white shadow-[0_10px_22px_rgba(1,184,255,0.18)]"
};

export function StatCard({ title, value, caption, icon, tone }: StatCardProps) {
  return (
    <div className="panel overflow-hidden">
      <div className="flex min-h-[168px] items-start justify-between gap-4 p-5">
        <div className="min-w-0 space-y-2">
          <p className="text-sm font-medium text-horizon-muted">{title}</p>
          <h3 className="break-words text-3xl font-bold tracking-tight text-horizon-text">{value}</h3>
          <p className="text-xs leading-5 text-horizon-muted">{caption}</p>
        </div>
        <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${toneMap[tone]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}
