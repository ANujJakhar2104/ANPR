"use client";

import { AdminSummary } from "@/lib/api";

function Card({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent: string;
}) {
  return (
    <div className="flex-1 rounded-xl border border-border bg-surface p-4 shadow-card">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-subtle">{label}</span>
        <span className={`h-2 w-2 rounded-full ${accent}`} />
      </div>
      <div className="mt-2 text-2xl font-semibold text-ink">{value}</div>
      {sub && <div className="mt-1 text-xs text-subtle">{sub}</div>}
    </div>
  );
}

export default function SummaryCards({ summary }: { summary: AdminSummary }) {
  return (
    <div className="flex flex-wrap gap-3">
      <Card
        label="Users"
        value={summary.total_users}
        sub={Object.entries(summary.users_by_role)
          .map(([role, count]) => `${count} ${role}`)
          .join(" · ")}
        accent="bg-primary"
      />
      <Card
        label="Detections"
        value={summary.total_detections}
        sub={`${summary.detections_last_24h} in last 24h`}
        accent="bg-accent"
      />
      <Card
        label="Video jobs"
        value={summary.total_video_jobs}
        sub={`${summary.jobs_pending_or_processing} active · ${summary.jobs_failed} failed`}
        accent="bg-warn"
      />
    </div>
  );
}
