import type { ReactNode } from "react";

interface SectionCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
}

export function SectionCard({ title, subtitle, children, actions }: SectionCardProps) {
  return (
    <section className="panel overflow-hidden">
      <div className="panel-header">
        <div className="min-w-0">
          <h3 className="text-lg font-bold text-horizon-text">{title}</h3>
          {subtitle ? <p className="mt-1 text-sm text-horizon-muted">{subtitle}</p> : null}
        </div>
        {actions ? <div className="w-full min-w-0 sm:w-auto sm:shrink-0">{actions}</div> : null}
      </div>
      <div className="panel-body">{children}</div>
    </section>
  );
}
