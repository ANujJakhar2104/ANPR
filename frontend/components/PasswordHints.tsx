"use client";

type Rule = { label: string; met: boolean };

export default function PasswordHints({ password }: { password: string }) {
  const rules: Rule[] = [
    { label: "At least 10 characters", met: password.length >= 10 },
    { label: "One uppercase letter", met: /[A-Z]/.test(password) },
    { label: "One lowercase letter", met: /[a-z]/.test(password) },
    { label: "One digit", met: /\d/.test(password) },
    { label: "One special character", met: /[!@#$%^&*()\-_=+[\]{};:'",.<>/?\\|`~]/.test(password) },
  ];

  return (
    <ul className="mt-2 grid grid-cols-1 gap-1 text-xs sm:grid-cols-2">
      {rules.map((rule) => (
        <li
          key={rule.label}
          className={`flex items-center gap-1.5 ${rule.met ? "text-okgreen" : "text-muted"}`}
        >
          <span className="font-mono">{rule.met ? "✓" : "·"}</span>
          {rule.label}
        </li>
      ))}
    </ul>
  );
}
