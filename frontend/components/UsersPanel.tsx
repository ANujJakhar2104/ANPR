"use client";

import { useEffect, useState } from "react";
import { listRoles, listUsers, RoleInfo, updateUserRole, User } from "@/lib/api";

function formatTime(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function UsersPanel({ selfId }: { selfId: string }) {
  const [users, setUsers] = useState<User[] | null>(null);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    listUsers().then(setUsers);
    listRoles().then(setRoles);
  }

  useEffect(refresh, []);

  async function handleRoleChange(userId: string, roleId: string) {
    setSavingId(userId);
    setError(null);
    try {
      const updated = await updateUserRole(userId, roleId);
      setUsers((prev) => prev?.map((u) => (u.id === userId ? updated : u)) ?? null);
    } catch {
      setError("Couldn't update that role - try again.");
    } finally {
      setSavingId(null);
    }
  }

  if (!users) {
    return <div className="rounded-xl border border-border bg-surface p-5 text-sm text-subtle shadow-card">Loading users...</div>;
  }

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
      {error && <p className="px-4 pt-4 text-sm text-danger">{error}</p>}
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border bg-sunken text-subtle">
            <th className="px-4 py-2.5 font-medium">Username</th>
            <th className="px-4 py-2.5 font-medium">Email</th>
            <th className="px-4 py-2.5 font-medium">Joined</th>
            <th className="px-4 py-2.5 font-medium">Role</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} className="border-b border-border last:border-0 hover:bg-sunken/60">
              <td className="px-4 py-2.5 font-medium text-ink">
                {u.username}
                {u.id === selfId && <span className="ml-2 text-xs font-normal text-faint">(you)</span>}
              </td>
              <td className="px-4 py-2.5 text-xs text-subtle">{u.email}</td>
              <td className="px-4 py-2.5 text-xs text-subtle">{formatTime(u.created_at)}</td>
              <td className="px-4 py-2.5">
                <select
                  value={u.role.id}
                  disabled={savingId === u.id || u.id === selfId}
                  onChange={(e) => handleRoleChange(u.id, e.target.value)}
                  className="rounded-lg border border-border bg-white px-2 py-1 text-xs font-medium text-ink outline-none focus:border-primary disabled:opacity-50"
                  title={u.id === selfId ? "You can't change your own role" : undefined}
                >
                  {roles.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.display_name}
                    </option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
