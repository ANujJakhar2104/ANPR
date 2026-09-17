"use client";

import { Fragment, useState } from "react";
import { ApiError, Detection, detectImage, detectVideo, Job, RoleInfo } from "@/lib/api";
import CharAnalysisStrip from "./CharAnalysisStrip";

export default function UploadPanel({
  role,
  onJobCreated,
}: {
  role: RoleInfo;
  onJobCreated: (job: Job) => void;
}) {
  const [mode, setMode] = useState<"image" | "video">("image");
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const canUseVideo = role.can_use_video;
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imageResult, setImageResult] = useState<{ detections: Detection[]; annotated: string } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Choose a file first");
      return;
    }
    if (mode === "video" && !canUseVideo) {
      setError("Video detection isn't included in your role.");
      return;
    }
    setLoading(true);
    setError(null);
    setImageResult(null);
    try {
      if (mode === "image") {
        const result = await detectImage(file);
        setImageResult({ detections: result.detections, annotated: result.annotated_image_base64 });
      } else {
        const job = await detectVideo(file);
        onJobCreated(job);
        setFile(null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed - try again");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
      <div className="mb-4 flex gap-1 border-b border-border pb-4">
        {(["image", "video"] as const).map((m) => (
          <button
            key={m}
            onClick={() => {
              setMode(m);
              setImageResult(null);
              setError(null);
            }}
            className={`flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${
              mode === m ? "bg-primary text-white" : "text-subtle hover:bg-sunken hover:text-ink"
            }`}
          >
            {m === "image" ? "Photo" : "Video"}
            {m === "video" && !canUseVideo && <span className="text-xs">🔒</span>}
          </button>
        ))}
      </div>

      {mode === "video" && !canUseVideo ? (
        <div className="rounded-lg bg-sunken px-4 py-6 text-center">
          <p className="text-sm text-ink">Video detection isn't included in your role.</p>
          <p className="mt-1 text-xs text-subtle">Ask an admin to move you to a role with video access.</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label className="text-sm text-subtle">
            {mode === "image"
              ? "Single frame - runs immediately, no job to track."
              : "Full clip - queued as a background job, watch its status in the log."}
          </label>
          <input
            type="file"
            accept={mode === "image" ? "image/*" : "video/*"}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm text-ink file:mr-3 file:rounded-lg file:border-0 file:bg-primary-soft file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-primary"
          />
          {error && <p className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-fit rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Reading plates..." : mode === "image" ? "Run detection" : "Queue video"}
          </button>
        </form>
      )}

      {imageResult && (
        <div className="mt-6 border-t border-border pt-5">
          <img
            src={`data:image/jpeg;base64,${imageResult.annotated}`}
            alt="Annotated detection result"
            className="mb-4 w-full rounded-lg border border-border"
          />
          {imageResult.detections.length === 0 ? (
            <p className="text-sm text-subtle">No plate matched to a vehicle in this frame.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-subtle">
                  <th className="py-1.5 pr-3 font-medium">Car ID</th>
                  <th className="py-1.5 pr-3 font-medium">Plate</th>
                  <th className="py-1.5 pr-3 font-medium">Confidence</th>
                  <th className="py-1.5 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {imageResult.detections.map((d, i) => (
                  <Fragment key={i}>
                    <tr className="border-b border-border/70">
                      <td className="py-2 pr-3">{d.car_id}</td>
                      <td className="py-2 pr-3 font-mono font-medium text-primary">{d.license_number ?? "UNREADABLE"}</td>
                      <td className="py-2 pr-3 text-subtle">
                        {d.license_number_score ? `${Math.round(d.license_number_score * 100)}%` : "-"}
                      </td>
                      <td className="py-2 text-right">
                        <button
                          onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
                          className="rounded-md border border-border px-2 py-1 text-xs font-medium text-ink transition-colors hover:border-primary hover:text-primary"
                        >
                          {expandedIdx === i ? "Hide" : "Analyze"}
                        </button>
                      </td>
                    </tr>
                    {expandedIdx === i && (
                      <tr className="border-b border-border/70">
                        <td colSpan={4} className="py-3">
                          <CharAnalysisStrip analysis={d.char_analysis} rawText={d.raw_ocr_text} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
