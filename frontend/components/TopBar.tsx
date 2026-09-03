"use client";

import { clearToken } from "@/lib/auth";
import { useRouter } from "next/navigation";

export default function TopBar({ username }: { username?: string }) {
  const router = useRouter();

  function logout() {
    clearToken();
    router.push("/login");
  }

  return (
    <header className="border-b border-hairline bg-panel">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <div className="flex items-baseline gap-2">
          <span className="text-lg font-semibold tracking-tight text-ink">ANPR Console</span>
          <span className="font-mono text-xs text-muted">plate reader</span>
        </div>
        {username && (
          <div className="flex items-center gap-4">
            <span className="font-mono text-sm text-muted">{username}</span>
            <button
              onClick={logout}
              className="rounded-sm border border-hairline px-3 py-1.5 text-sm text-ink transition-colors hover:border-amber hover:text-amber"
            >
              Log out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
