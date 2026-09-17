"use client";

import { useEffect, useState } from "react";
import { ApiError, createRole, deleteRole, listRoles, RoleInfo, updateRole } from "@/lib/api";

const EMPTY_FORM = { name: "", display_name: "", description: "", can_use_video: false, is_admin: false, is_default: false };

function Toggle({
  checked,
  onChange,
  disabled,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  label: string;
}) {
  return (
    <label className={`flex items-center gap-2 text-sm ${disabled ? "opacity-50" : ""}`}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${checked ? "bg-primary" : "bg-border"}`}
      >
        <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${checked ? "translate-x-[18px]" : "translate-x-0.5"}`} />
      </button>
      {label}
    </label>
  );
}

export default function RolesPanel() {
  const [roles, setRoles] = useState<RoleInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [creating, setCreating] = useState(false);

  function refresh() {
    listRoles().then(setRoles);
  }

  useEffect(refresh, []);

  async function patch(role: RoleInfo, changes: Partial<RoleInfo>) {
    setSavingId(role.id);
    setError(null);
    try {
      const updated = await updateRole(role.id, changes);
      setRoles((prev) => prev?.map((r) => (r.id === role.id ? updated : r)) ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't update that role.");
    } finally {
      setSavingId(null);
    }
  }

  async function handleDelete(role: RoleInfo) {
    if (!confirm(`Delete the "${role.display_name}" role? Users must be reassigned first.`)) return;
    setSavingId(role.id);
    setError(null);
    try {
      await deleteRole(role.id);
      setRoles((prev) => prev?.filter((r) => r.id !== role.id) ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't delete that role.");
    } finally {
      setSavingId(null);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const created = await createRole({
        name: form.name,
        display_name: form.display_name,
        description: form.description || undefined,
        can_use_video: form.can_use_video,
        is_admin: form.is_admin,
        is_default: form.is_default,
      });
      setRoles((prev) => [...(prev ?? []), created]);
      setForm(EMPTY_FORM);
      setShowCreate(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create that role.");
    } finally {
      setCreating(false);
    }
  }

  if (!roles) {
    return <div className="rounded-xl border border-border bg-surface p-5 text-sm text-subtle shadow-card">Loading roles...</div>;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-subtle">
          Roles control what a user can do. Toggle capabilities per role, or add an entirely custom one.
        </p>
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="rounded-lg bg-primary px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-dark"
        >
          {showCreate ? "Cancel" : "New role"}
        </button>
      </div>

      {error && <p className="rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}

      {showCreate && (
        <form onSubmit={handleCreate} className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-5 shadow-card">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-subtle">Display name</label>
              <input
                required
                value={form.display_name}
                onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value, name: f.name || e.target.value.toLowerCase().replace(/\s+/g, "_") }))}
                placeholder="e.g. Auditor"
                className="rounded-lg border border-border bg-white px-2.5 py-1.5 text-sm outline-none focus:border-primary"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-subtle">Slug (machine name)</label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. auditor"
                className="rounded-lg border border-border bg-white px-2.5 py-1.5 text-sm outline-none focus:border-primary"
              />
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-subtle">Description (optional)</label>
            <input
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              className="rounded-lg border border-border bg-white px-2.5 py-1.5 text-sm outline-none focus:border-primary"
            />
          </div>
          <div className="flex flex-wrap gap-5 pt-1">
            <Toggle label="Can use video detection" checked={form.can_use_video} onChange={(v) => setForm((f) => ({ ...f, can_use_video: v }))} />
            <Toggle label="Admin access" checked={form.is_admin} onChange={(v) => setForm((f) => ({ ...f, is_admin: v }))} />
            <Toggle label="Default for new signups" checked={form.is_default} onChange={(v) => setForm((f) => ({ ...f, is_default: v }))} />
          </div>
          <button
            type="submit"
            disabled={creating}
            className="mt-1 w-fit rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-dark disabled:opacity-50"
          >
            {creating ? "Creating..." : "Create role"}
          </button>
        </form>
      )}

      <div className="flex flex-col gap-3">
        {roles.map((role) => (
          <div key={role.id} className="rounded-xl border border-border bg-surface p-4 shadow-card">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-ink">{role.display_name}</span>
                  <span className="rounded-full bg-sunken px-2 py-0.5 text-xs text-faint">{role.name}</span>
                  {role.is_default && <span className="rounded-full bg-primary-soft px-2 py-0.5 text-xs font-medium text-primary">Default</span>}
                  {role.is_system && <span className="rounded-full bg-sunken px-2 py-0.5 text-xs text-faint">Built-in</span>}
                </div>
                {role.description && <p className="mt-0.5 text-xs text-subtle">{role.description}</p>}
              </div>
              {!role.is_system && (
                <button
                  onClick={() => handleDelete(role)}
                  disabled={savingId === role.id}
                  className="rounded-md border border-border px-2.5 py-1 text-xs font-medium text-danger transition-colors hover:border-danger disabled:opacity-50"
                >
                  Delete
                </button>
              )}
            </div>
            <div className="mt-3 flex flex-wrap gap-5 border-t border-border pt-3">
              <Toggle
                label="Video detection"
                checked={role.can_use_video}
                disabled={savingId === role.id}
                onChange={(v) => patch(role, { can_use_video: v })}
              />
              <Toggle
                label="Admin access"
                checked={role.is_admin}
                disabled={savingId === role.id}
                onChange={(v) => patch(role, { is_admin: v })}
              />
              <Toggle
                label="Default for new signups"
                checked={role.is_default}
                disabled={savingId === role.id}
                onChange={(v) => patch(role, { is_default: v })}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
