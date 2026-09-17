"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AdminSummary, getAdminSummary, getMe, User } from "@/lib/api";
import { getToken } from "@/lib/auth";
import AppShell from "@/components/AppShell";
import SummaryCards from "@/components/SummaryCards";
import SystemHealthPanel from "@/components/SystemHealthPanel";
import AuditLogPanel from "@/components/AuditLogPanel";
import UsersPanel from "@/components/UsersPanel";
import RolesPanel from "@/components/RolesPanel";
import PasswordPolicyPanel from "@/components/PasswordPolicyPanel";

type Tab = "overview" | "users" | "roles" | "password-policy" | "audit";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "users", label: "Users" },
  { id: "roles", label: "Roles" },
  { id: "password-policy", label: "Password policy" },
  { id: "audit", label: "Audit log" },
];

export default function AdminPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    getMe()
      .then((u) => {
        if (!u.role.is_admin) {
          setDenied(true);
          return;
        }
        setUser(u);
        getAdminSummary().then(setSummary);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  if (denied) {
    return (
      <AppShell breadcrumb="Admin">
        <div className="rounded-xl border border-border bg-surface p-6 shadow-card">
          <p className="text-sm text-danger">Admin access required.</p>
        </div>
      </AppShell>
    );
  }

  if (!user) {
    return (
      <AppShell breadcrumb="Admin">
        <div className="text-sm text-subtle">Loading...</div>
      </AppShell>
    );
  }

  return (
    <AppShell user={user} breadcrumb="Admin">
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-ink">Admin</h1>
            <p className="mt-0.5 text-sm text-subtle">Manage roles, password policy, users and audit activity.</p>
          </div>
        </div>

        <div className="flex gap-1 overflow-x-auto rounded-xl border border-border bg-surface p-1.5 shadow-card">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`whitespace-nowrap rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${
                tab === t.id ? "bg-primary text-white" : "text-subtle hover:bg-sunken hover:text-ink"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "overview" && (
          <div className="flex flex-col gap-4">
            {summary && <SummaryCards summary={summary} />}
            <SystemHealthPanel />
          </div>
        )}
        {tab === "users" && <UsersPanel selfId={user.id} />}
        {tab === "roles" && <RolesPanel />}
        {tab === "password-policy" && <PasswordPolicyPanel />}
        {tab === "audit" && <AuditLogPanel />}
      </div>
    </AppShell>
  );
}
