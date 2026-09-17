"use client";

import { useEffect, useState } from "react";
import { AuditLogEntry, AuditLogFilters, exportAuditLogs, listAuditLogs } from "@/lib/api";
import ExportButtons from "./ExportButtons";
import Pagination from "./Pagination";

const PAGE_SIZE = 20;

const ACTIONS = [
  "USER_REGISTER", "USER_LOGIN_SUCCESS", "USER_LOGIN_FAILURE", "TOKEN_VERIFY_FAILURE",
  "ROLE_DENIED", "DETECTION_IMAGE_REQUEST", "DETECTION_IMAGE_SUCCESS", "DETECTION_IMAGE_FAILURE",
  "DETECTION_VIDEO_REQUEST", "DETECTION_VIDEO_SUCCESS", "DETECTION_VIDEO_FAILURE",
  "JOB_STATUS_CHECK", "RESULT_DOWNLOAD", "DETECTIONS_EXPORT", "AUDIT_EXPORT",
  "ADMIN_ROLE_CHANGE", "ADMIN_ROLE_CREATED", "ADMIN_ROLE_UPDATED", "ADMIN_ROLE_DELETED",
  "ADMIN_PASSWORD_POLICY_UPDATED", "SYSTEM_HEALTH_CHECK",
];

function formatTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function AuditLogPanel() {
  const [action, setAction] = useState("");
  const [statusFilter, setStatusFilter] = useState<"" | "success" | "failure">("");
  const [username, setUsername] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ items: AuditLogEntry[]; total: number } | null>(null);
  const [loading, setLoading] = useState(false);

  function buildFilters(): AuditLogFilters {
    return {
      action: action || undefined,
      status: statusFilter || undefined,
      username: username || undefined,
      page,
      page_size: PAGE_SIZE,
    };
  }

  useEffect(() => {
    setLoading(true);
    listAuditLogs(buildFilters())
      .then((res) => setData({ items: res.items, total: res.total }))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [action, statusFilter, username, page]);

  useEffect(() => setPage(1), [action, statusFilter, username]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3 rounded-xl border border-border bg-surface p-4 shadow-card">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-subtle">Action</label>
            <select
              value={action}
              onChange={(e) => setAction(e.target.value)}
              className="rounded-lg border border-border bg-white px-2.5 py-1.5 text-sm text-ink outline-none focus:border-primary"
            >
              <option value="">All</option>
              {ACTIONS.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-subtle">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as "" | "success" | "failure")}
              className="rounded-lg border border-border bg-white px-2.5 py-1.5 text-sm text-ink outline-none focus:border-primary"
            >
              <option value="">All</option>
              <option value="success">Success</option>
              <option value="failure">Failure</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-subtle">Username contains</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="rounded-lg border border-border bg-white px-2.5 py-1.5 text-sm text-ink outline-none focus:border-primary"
            />
          </div>
        </div>
        <ExportButtons onExport={(format) => exportAuditLogs(format, buildFilters())} />
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-sunken text-subtle">
              <th className="px-4 py-2.5 font-medium">Time</th>
              <th className="px-4 py-2.5 font-medium">User</th>
              <th className="px-4 py-2.5 font-medium">Action</th>
              <th className="px-4 py-2.5 font-medium">Status</th>
              <th className="px-4 py-2.5 font-medium">Detail</th>
              <th className="px-4 py-2.5 font-medium">IP</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-sm text-subtle">
                  Loading...
                </td>
              </tr>
            )}
            {!loading && data?.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-sm text-subtle">
                  No log entries match these filters.
                </td>
              </tr>
            )}
            {!loading &&
              data?.items.map((entry) => (
                <tr key={entry.id} className="border-b border-border last:border-0 hover:bg-sunken/60">
                  <td className="px-4 py-2.5 text-xs text-subtle">{formatTime(entry.timestamp)}</td>
                  <td className="px-4 py-2.5 font-mono text-xs">{entry.username ?? "-"}</td>
                  <td className="px-4 py-2.5 font-mono text-xs">{entry.action}</td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                        entry.status === "failure" ? "bg-danger-soft text-danger" : "bg-success-soft text-success"
                      }`}
                    >
                      {entry.status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-subtle">{entry.detail ?? "-"}</td>
                  <td className="px-4 py-2.5 font-mono text-xs text-subtle">{entry.ip_address ?? "-"}</td>
                </tr>
              ))}
          </tbody>
        </table>
        {data && <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPageChange={setPage} />}
      </div>
    </div>
  );
}
