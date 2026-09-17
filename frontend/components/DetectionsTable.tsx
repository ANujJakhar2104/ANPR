"use client";

import { Fragment, useEffect, useState } from "react";
import {
  DetectionFilters,
  DetectionRecord,
  exportDetections,
  listDetections,
  RoleInfo,
} from "@/lib/api";
import ExportButtons from "./ExportButtons";
import Pagination from "./Pagination";
import CharAnalysisStrip from "./CharAnalysisStrip";

const PAGE_SIZE = 15;

function formatTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DetectionsTable({ role, selfId }: { role: RoleInfo; selfId: string }) {
  const [source, setSource] = useState<"" | "image" | "video">("");
  const [plate, setPlate] = useState("");
  const [onlyMine, setOnlyMine] = useState(false);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ items: DetectionRecord[]; total: number } | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const isAdmin = role.is_admin;

  function buildFilters(): DetectionFilters {
    return {
      source: source || undefined,
      plate: plate || undefined,
      user_id: isAdmin && onlyMine ? selfId : undefined,
      page,
      page_size: PAGE_SIZE,
    };
  }

  useEffect(() => {
    setLoading(true);
    listDetections(buildFilters())
      .then((res) => setData({ items: res.items, total: res.total }))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, plate, onlyMine, page]);

  useEffect(() => setPage(1), [source, plate, onlyMine]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3 rounded-xl border border-border bg-surface p-4 shadow-card">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-subtle">Source</label>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value as "" | "image" | "video")}
              className="rounded-lg border border-border bg-white px-2.5 py-1.5 text-sm text-ink outline-none focus:border-primary"
            >
              <option value="">All</option>
              <option value="image">Photo</option>
              <option value="video">Video</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-subtle">Plate contains</label>
            <input
              value={plate}
              onChange={(e) => setPlate(e.target.value)}
              placeholder="e.g. DL9C"
              className="rounded-lg border border-border bg-white px-2.5 py-1.5 text-sm text-ink outline-none focus:border-primary"
            />
          </div>
          {isAdmin && (
            <label className="flex items-center gap-2 pb-1.5 text-xs text-subtle">
              <input type="checkbox" checked={onlyMine} onChange={(e) => setOnlyMine(e.target.checked)} />
              Only my detections
            </label>
          )}
        </div>
        <ExportButtons onExport={(format) => exportDetections(format, buildFilters())} />
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-sunken text-subtle">
              <th className="px-4 py-2.5 font-medium">Time</th>
              <th className="px-4 py-2.5 font-medium">Source</th>
              <th className="px-4 py-2.5 font-medium">Car ID</th>
              <th className="px-4 py-2.5 font-medium">Plate</th>
              <th className="px-4 py-2.5 font-medium">Confidence</th>
              {isAdmin && !onlyMine && <th className="px-4 py-2.5 font-medium">User</th>}
              <th className="px-4 py-2.5 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-sm text-subtle">
                  Loading...
                </td>
              </tr>
            )}
            {!loading && data?.items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-sm text-subtle">
                  No detections match these filters.
                </td>
              </tr>
            )}
            {!loading &&
              data?.items.map((d) => (
                <Fragment key={d.id}>
                  <tr className="border-b border-border last:border-0 hover:bg-sunken/60">
                    <td className="px-4 py-2.5 text-xs text-subtle">{formatTime(d.created_at)}</td>
                    <td className="px-4 py-2.5 text-xs capitalize text-subtle">{d.source}</td>
                    <td className="px-4 py-2.5 font-mono">{d.car_id}</td>
                    <td className="px-4 py-2.5 font-mono font-medium text-primary">{d.license_number ?? "UNREADABLE"}</td>
                    <td className="px-4 py-2.5 text-xs text-subtle">
                      {d.license_number_score ? `${Math.round(parseFloat(d.license_number_score) * 100)}%` : "-"}
                    </td>
                    {isAdmin && !onlyMine && (
                      <td className="px-4 py-2.5 font-mono text-xs text-subtle">{d.user_id.slice(0, 8)}</td>
                    )}
                    <td className="px-4 py-2.5 text-right">
                      <button
                        onClick={() => setExpandedId(expandedId === d.id ? null : d.id)}
                        className="rounded-md border border-border px-2 py-1 text-xs font-medium text-ink transition-colors hover:border-primary hover:text-primary"
                      >
                        {expandedId === d.id ? "Hide" : "Analyze"}
                      </button>
                    </td>
                  </tr>
                  {expandedId === d.id && (
                    <tr className="border-b border-border bg-sunken/60 last:border-0">
                      <td colSpan={7} className="px-4 py-4">
                        <CharAnalysisStrip analysis={d.char_analysis} rawText={d.raw_ocr_text} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
          </tbody>
        </table>
        {data && <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPageChange={setPage} />}
      </div>
    </div>
  );
}
