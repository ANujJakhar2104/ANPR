"use client";

import { useEffect, useState } from "react";
import { ApiError, getPasswordPolicy, PasswordPolicy, updatePasswordPolicy } from "@/lib/api";

const RULE_TOGGLES: { key: keyof PasswordPolicy; label: string; hint: string }[] = [
  { key: "require_uppercase", label: "Require an uppercase letter", hint: "A-Z" },
  { key: "require_lowercase", label: "Require a lowercase letter", hint: "a-z" },
  { key: "require_digit", label: "Require a digit", hint: "0-9" },
  { key: "require_special", label: "Require a special character", hint: "!@#$..." },
  { key: "block_common_passwords", label: "Block common/breached passwords", hint: "e.g. \"password1\"" },
  { key: "block_username_in_password", label: "Block username/email inside password", hint: "" },
];

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${checked ? "bg-primary" : "bg-border"}`}
    >
      <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${checked ? "translate-x-[18px]" : "translate-x-0.5"}`} />
    </button>
  );
}

export default function PasswordPolicyPanel() {
  const [policy, setPolicy] = useState<PasswordPolicy | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getPasswordPolicy().then(setPolicy);
  }, []);

  async function handleSave() {
    if (!policy) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updatePasswordPolicy(policy);
      setPolicy(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save the policy.");
    } finally {
      setSaving(false);
    }
  }

  if (!policy) {
    return <div className="rounded-xl border border-border bg-surface p-5 text-sm text-subtle shadow-card">Loading policy...</div>;
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-subtle">
        Choose exactly which rules apply to new passwords. Changes take effect immediately for every new registration
        and password change - the live checklist on the register page mirrors this automatically.
      </p>

      <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
        <div className="grid grid-cols-1 gap-4 border-b border-border pb-5 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-subtle">Minimum length</label>
            <input
              type="number"
              min={6}
              max={64}
              value={policy.min_length}
              onChange={(e) => setPolicy({ ...policy, min_length: Number(e.target.value) })}
              className="rounded-lg border border-border bg-white px-2.5 py-1.5 text-sm outline-none focus:border-primary"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-subtle">Maximum length</label>
            <input
              type="number"
              min={8}
              max={256}
              value={policy.max_length}
              onChange={(e) => setPolicy({ ...policy, max_length: Number(e.target.value) })}
              className="rounded-lg border border-border bg-white px-2.5 py-1.5 text-sm outline-none focus:border-primary"
            />
          </div>
        </div>

        <div className="flex flex-col gap-3 pt-4">
          {RULE_TOGGLES.map((rule) => (
            <div key={rule.key} className="flex items-center justify-between">
              <div>
                <div className="text-sm text-ink">{rule.label}</div>
                {rule.hint && <div className="text-xs text-faint">{rule.hint}</div>}
              </div>
              <Toggle
                checked={Boolean(policy[rule.key])}
                onChange={(v) => setPolicy({ ...policy, [rule.key]: v })}
              />
            </div>
          ))}
        </div>

        {error && <p className="mt-4 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}

        <div className="mt-5 flex items-center gap-3 border-t border-border pt-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-dark disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save policy"}
          </button>
          {saved && <span className="text-sm text-success">Saved.</span>}
        </div>
      </div>
    </div>
  );
}
