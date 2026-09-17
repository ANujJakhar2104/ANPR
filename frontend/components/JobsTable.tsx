"use client";

import { useState } from "react";
import { downloadJob, Job } from "@/lib/api";

const STATUS_STYLES: Record<Job["status"], string> = {
  pending: "bg-sunken text-subtle",
  processing: "bg-warn-soft text-warn",
  completed: "bg-success-soft text-success",
  failed: "bg-danger-soft text-danger",
};

function formatTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function JobsTable({ jobs }: { jobs: Job[] }) {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  async function handleDownload(job: Job) {
    setDownloadingId(job.id);
    try {
      await downloadJob(job.id, `${job.input_filename}_annotated.mp4`);
    } finally {
      setDownloadingId(null);
    }
  }

  if (jobs.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-surface p-5 text-sm text-subtle shadow-card">
        No video jobs queued yet. Upload a clip to see it appear here.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border bg-sunken text-subtle">
            <th className="px-4 py-2.5 font-medium">Job</th>
            <th className="px-4 py-2.5 font-medium">File</th>
            <th className="px-4 py-2.5 font-medium">Status</th>
            <th className="px-4 py-2.5 font-medium">Queued</th>
            <th className="px-4 py-2.5 font-medium"></th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className="border-b border-border last:border-0 hover:bg-sunken/60">
              <td className="px-4 py-2.5 font-mono text-xs text-faint">{job.id.slice(0, 8)}</td>
              <td className="px-4 py-2.5 text-ink">{job.input_filename}</td>
              <td className="px-4 py-2.5">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[job.status]}`}>
                  {job.status}
                </span>
                {job.status === "failed" && job.error_message && (
                  <span className="ml-2 text-xs text-subtle">({job.error_message})</span>
                )}
              </td>
              <td className="px-4 py-2.5 text-xs text-subtle">{formatTime(job.created_at)}</td>
              <td className="px-4 py-2.5 text-right">
                {job.status === "completed" && (
                  <button
                    onClick={() => handleDownload(job)}
                    disabled={downloadingId === job.id}
                    className="rounded-md border border-border px-2.5 py-1 text-xs font-medium text-ink transition-colors hover:border-primary hover:text-primary disabled:opacity-50"
                  >
                    {downloadingId === job.id ? "Fetching..." : "Download"}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
