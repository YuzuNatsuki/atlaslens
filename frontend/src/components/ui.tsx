/**
 * Shared UI primitives for AtlasLens pages.
 * Tiny on purpose — page components compose these directly.
 */

import { ReactNode } from "react";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2 sm:gap-4 mb-4 sm:mb-6">
      <div className="min-w-0">
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

export function SectionHeader({
  title,
  subtitle,
  actions,
  icon,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 sm:gap-3 mb-2">
      <div className="min-w-0">
        <h2 className="section-title">
          {icon}
          {title}
        </h2>
        {subtitle && <p className="section-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2 shrink-0">{actions}</div>}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="border border-dashed border-slate-300 rounded-xl bg-slate-50/60 px-6 py-8 text-center">
      {icon && <div className="flex justify-center mb-2 text-slate-400">{icon}</div>}
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {description && (
        <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">{description}</p>
      )}
      {action && <div className="mt-3 flex justify-center">{action}</div>}
    </div>
  );
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card grid gap-2">
      <div className="skeleton h-4 w-1/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton h-3" style={{ width: `${80 - i * 12}%` }} />
      ))}
    </div>
  );
}

export function InlineAlert({
  tone = "info",
  children,
}: {
  tone?: "info" | "error" | "warn" | "success";
  children: ReactNode;
}) {
  const toneClass = {
    info: "bg-brand/5 border-brand/20 text-brand-dark",
    error: "bg-rose-50 border-rose-200 text-rose-700",
    warn: "bg-amber-50 border-amber-200 text-amber-800",
    success: "bg-emerald-50 border-emerald-200 text-emerald-700",
  }[tone];
  return (
    <div className={`text-xs border rounded-lg px-2.5 py-1.5 ${toneClass}`}>
      {children}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-500">
      <span className="h-3 w-3 rounded-full border-2 border-brand/30 border-t-brand animate-spin" />
      {label}
    </span>
  );
}

export function formatJpDate(iso?: string | null): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString("ja-JP", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
