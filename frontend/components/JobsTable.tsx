"use client";

import { useState } from "react";
import { downloadJob, Job } from "@/lib/api";

const STATUS_STYLES: Record<Job["status"], string> = {
  pending: "text-muted",
  processing: "text-amber",
  completed: "text-okgreen",
  failed: "text-danger",
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
      <div className="border border-hairline bg-panel p-5 text-sm text-muted">
        No video jobs queued yet. Upload a clip to see it appear here.
      </div>
    );
  }

  return (
    <div className="border border-hairline bg-panel">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-hairline text-muted">
            <th className="px-4 py-2.5 font-normal">Job</th>
            <th className="px-4 py-2.5 font-normal">File</th>
            <th className="px-4 py-2.5 font-normal">Status</th>
            <th className="px-4 py-2.5 font-normal">Queued</th>
            <th className="px-4 py-2.5 font-normal"></th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className="border-b border-hairline/50 last:border-0">
              <td className="px-4 py-2.5 font-mono text-xs text-muted">{job.id.slice(0, 8)}</td>
              <td className="px-4 py-2.5 text-ink">{job.input_filename}</td>
              <td className={`px-4 py-2.5 font-mono text-xs uppercase ${STATUS_STYLES[job.status]}`}>
                {job.status}
                {job.status === "failed" && job.error_message && (
                  <span className="ml-2 normal-case text-muted">({job.error_message})</span>
                )}
              </td>
              <td className="px-4 py-2.5 font-mono text-xs text-muted">{formatTime(job.created_at)}</td>
              <td className="px-4 py-2.5 text-right">
                {job.status === "completed" && (
                  <button
                    onClick={() => handleDownload(job)}
                    disabled={downloadingId === job.id}
                    className="border border-hairline px-2.5 py-1 text-xs text-ink transition-colors hover:border-amber hover:text-amber disabled:opacity-50"
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
