"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/auth";
import { User } from "@/lib/api";

function CarIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <path
        d="M4 16.5V11l1.6-4.2A2 2 0 0 1 7.5 5.5h9a2 2 0 0 1 1.9 1.3L20 11v5.5M4 16.5a1.5 1.5 0 0 0 1.5 1.5h1a1.5 1.5 0 0 0 1.5-1.5M4 16.5V18a1 1 0 0 0 1 1h1M20 16.5a1.5 1.5 0 0 1-1.5 1.5h-1a1.5 1.5 0 0 1-1.5-1.5M20 16.5V18a1 1 0 0 1-1 1h-1"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="7.5" cy="16.5" r="1.25" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="16.5" cy="16.5" r="1.25" stroke="currentColor" strokeWidth="1.4" />
      <path d="M4 11h16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

const ICONS: Record<string, (p: { className?: string }) => JSX.Element> = {
  upload: ({ className = "h-5 w-5" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <path d="M12 16V4M12 4l-4 4M12 4l4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  grid: ({ className = "h-5 w-5" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <rect x="4" y="4" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
      <rect x="13" y="4" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
      <rect x="4" y="13" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
      <rect x="13" y="13" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  ),
  shield: ({ className = "h-5 w-5" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <path
        d="M12 3.5l7 2.6v5.2c0 4.6-2.9 7.9-7 9.2-4.1-1.3-7-4.6-7-9.2V6.1l7-2.6z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  ),
};

const LINKS = [
  { href: "/dashboard", label: "Upload", icon: "upload" },
  { href: "/detections", label: "Detections", icon: "grid" },
];

export default function AppShell({
  user,
  breadcrumb,
  children,
}: {
  user?: User;
  breadcrumb: string;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();

  function logout() {
    clearToken();
    router.push("/login");
  }

  const links = [...LINKS, ...(user?.role.is_admin ? [{ href: "/admin", label: "Admin", icon: "shield" }] : [])];

  return (
    <div className="flex min-h-screen bg-canvas">
      <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-surface">
        <div className="flex items-center gap-2 px-5 py-5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-white">
            <CarIcon className="h-[18px] w-[18px]" />
          </span>
          <span className="text-[15px] font-semibold tracking-tight text-ink">ANPR Console</span>
        </div>

        {user && (
          <nav className="mt-2 flex flex-col gap-0.5 px-3">
            {links.map((link) => {
              const Icon = ICONS[link.icon];
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                    active ? "bg-primary text-white" : "text-subtle hover:bg-sunken hover:text-ink"
                  }`}
                >
                  <Icon className="h-[18px] w-[18px]" />
                  {link.label}
                </Link>
              );
            })}
          </nav>
        )}

        <div className="mt-auto p-3">
          {user && (
            <div className="flex items-center gap-2.5 rounded-lg border border-border bg-sunken px-3 py-2.5">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-soft text-xs font-semibold text-primary">
                {user.username.slice(0, 2).toUpperCase()}
              </span>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-ink">{user.username}</div>
                <div className="truncate text-xs text-subtle">{user.role.display_name}</div>
              </div>
              <button
                onClick={logout}
                title="Log out"
                className="rounded-md p-1.5 text-faint transition-colors hover:bg-white hover:text-danger"
              >
                <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4">
                  <path d="M15 17l5-5-5-5M20 12H9M13 5H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </aside>

      <div className="flex min-h-screen flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border bg-surface px-8 py-4">
          <div className="flex items-center gap-1.5 text-sm">
            <span className="text-faint">Home</span>
            <span className="text-faint">/</span>
            <span className="font-medium text-ink">{breadcrumb}</span>
          </div>
        </header>
        <main className="flex-1 px-8 py-7">{children}</main>
      </div>
    </div>
  );
}
