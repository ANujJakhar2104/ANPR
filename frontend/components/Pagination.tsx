"use client";

export default function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}) {
  const lastPage = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="flex items-center justify-between border-t border-border px-4 py-2.5 text-xs text-subtle">
      <span>
        {total === 0 ? "0 rows" : `${(page - 1) * pageSize + 1}-${Math.min(page * pageSize, total)} of ${total}`}
      </span>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="rounded-md border border-border px-2.5 py-1 transition-colors hover:border-primary hover:text-primary disabled:opacity-30"
        >
          Prev
        </button>
        <span>
          {page} / {lastPage}
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= lastPage}
          className="rounded-md border border-border px-2.5 py-1 transition-colors hover:border-primary hover:text-primary disabled:opacity-30"
        >
          Next
        </button>
      </div>
    </div>
  );
}
