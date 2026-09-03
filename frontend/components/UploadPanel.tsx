"use client";

import { useState } from "react";
import { ApiError, Detection, detectImage, detectVideo, Job } from "@/lib/api";

export default function UploadPanel({ onJobCreated }: { onJobCreated: (job: Job) => void }) {
  const [mode, setMode] = useState<"image" | "video">("image");
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
    <div className="border border-hairline bg-panel p-5">
      <div className="mb-4 flex gap-1 border-b border-hairline pb-4">
        {(["image", "video"] as const).map((m) => (
          <button
            key={m}
            onClick={() => {
              setMode(m);
              setImageResult(null);
              setError(null);
            }}
            className={`px-3 py-1.5 text-sm transition-colors ${
              mode === m ? "bg-amber text-asphalt" : "text-muted hover:text-ink"
            }`}
          >
            {m === "image" ? "Photo" : "Video"}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label className="text-sm text-muted">
          {mode === "image"
            ? "Single frame - runs immediately, no job to track."
            : "Full clip - queued as a background job, watch its status in the log."}
        </label>
        <input
          type="file"
          accept={mode === "image" ? "image/*" : "video/*"}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm text-ink file:mr-3 file:border-0 file:bg-hairline file:px-3 file:py-1.5 file:text-ink"
        />
        {error && <p className="text-sm text-danger">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-fit border border-amber px-4 py-2 text-sm font-medium text-amber transition-colors hover:bg-amber hover:text-asphalt disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Reading plates..." : mode === "image" ? "Run detection" : "Queue video"}
        </button>
      </form>

      {imageResult && (
        <div className="mt-6 border-t border-hairline pt-5">
          <img
            src={`data:image/jpeg;base64,${imageResult.annotated}`}
            alt="Annotated detection result"
            className="mb-4 w-full border border-hairline"
          />
          {imageResult.detections.length === 0 ? (
            <p className="text-sm text-muted">No plate matched to a vehicle in this frame.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-hairline text-muted">
                  <th className="py-1.5 pr-3 font-normal">Car ID</th>
                  <th className="py-1.5 pr-3 font-normal">Plate</th>
                  <th className="py-1.5 font-normal">Confidence</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {imageResult.detections.map((d, i) => (
                  <tr key={i} className="border-b border-hairline/50">
                    <td className="py-1.5 pr-3">{d.car_id}</td>
                    <td className="py-1.5 pr-3 text-amber">{d.license_number ?? "UNREADABLE"}</td>
                    <td className="py-1.5 text-muted">
                      {d.license_number_score ? `${Math.round(d.license_number_score * 100)}%` : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
