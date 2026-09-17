"use client";

import { CharAnalysisEntry } from "@/lib/api";

export default function CharAnalysisStrip({
  analysis,
  rawText,
}: {
  analysis: CharAnalysisEntry[] | null;
  rawText: string | null;
}) {
  if (!analysis) {
    return (
      <p className="text-xs text-subtle">
        {rawText
          ? `OCR read "${rawText}" but it didn't match the 10-character plate format, so no position-by-position breakdown.`
          : "No OCR text captured for this reading."}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-1">
        {analysis.map((c) => (
          <div
            key={c.position}
            title={`Position ${c.position} - expected ${c.expected_type}${c.was_corrected ? ` - OCR read '${c.raw_char}', corrected to '${c.corrected_char}'` : ""}`}
            className={`flex h-12 w-9 flex-col items-center justify-center rounded-md border font-mono text-sm ${
              c.was_corrected ? "border-warn bg-warn-soft text-warn" : "border-border bg-sunken text-ink"
            }`}
          >
            <span>{c.corrected_char}</span>
            <span className="text-[10px] text-faint">{c.expected_type === "letter" ? "A" : "0"}</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-subtle">
        Amber cells were corrected from a different OCR guess based on the expected letter/digit position - hover a
        cell for the raw read.
      </p>
    </div>
  );
}
