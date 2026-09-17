"use client";

import { useState } from "react";

export default function ExportButtons({
  onExport,
}: {
  onExport: (format: "csv" | "html" | "pdf") => Promise<void>;
}) {
  const [busy, setBusy] = useState<string | null>(null);

  async function handle(format: "csv" | "html" | "pdf") {
    setBusy(format);
    try {
      await onExport(format);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex gap-1.5">
      {(["csv", "html", "pdf"] as const).map((format) => (
        <button
          key={format}
          onClick={() => handle(format)}
          disabled={busy !== null}
          className="rounded-md border border-border px-2.5 py-1.5 text-xs font-medium uppercase tracking-wide text-subtle transition-colors hover:border-primary hover:text-primary disabled:opacity-50"
        >
          {busy === format ? "..." : format}
        </button>
      ))}
    </div>
  );
}
