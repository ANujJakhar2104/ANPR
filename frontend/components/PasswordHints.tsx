"use client";

import { PasswordPolicy } from "@/lib/api";

const SPECIAL_RE = /[!@#$%^&*()\-_=+[\]{};:'",.<>/?\\|`~]/;

type Rule = { label: string; met: boolean };

export default function PasswordHints({ password, policy }: { password: string; policy: PasswordPolicy | null }) {
  if (!policy) return null;

  const rules: Rule[] = [
    { label: `At least ${policy.min_length} characters`, met: password.length >= policy.min_length },
    ...(policy.require_uppercase ? [{ label: "One uppercase letter", met: /[A-Z]/.test(password) }] : []),
    ...(policy.require_lowercase ? [{ label: "One lowercase letter", met: /[a-z]/.test(password) }] : []),
    ...(policy.require_digit ? [{ label: "One digit", met: /\d/.test(password) }] : []),
    ...(policy.require_special ? [{ label: "One special character", met: SPECIAL_RE.test(password) }] : []),
  ];

  return (
    <ul className="mt-1 grid grid-cols-1 gap-1 text-xs sm:grid-cols-2">
      {rules.map((rule) => (
        <li key={rule.label} className={`flex items-center gap-1.5 ${rule.met ? "text-success" : "text-faint"}`}>
          <span>{rule.met ? "✓" : "·"}</span>
          {rule.label}
        </li>
      ))}
    </ul>
  );
}
