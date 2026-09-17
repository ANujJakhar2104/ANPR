"use client";

import { useEffect, useState } from "react";
import { getSystemHealth, SystemHealth } from "@/lib/api";

const POLL_MS = 5000;

function formatBytes(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(1)} ${units[unit]}`;
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${days}d ${hours}h ${mins}m`;
}

function Meter({ label, percent, sub }: { label: string; percent: number; sub: string }) {
  const color = percent > 85 ? "bg-danger" : percent > 65 ? "bg-warn" : "bg-success";
  return (
    <div className="flex-1">
      <div className="flex items-baseline justify-between text-xs text-subtle">
        <span>{label}</span>
        <span className="font-medium text-ink">{percent.toFixed(0)}%</span>
      </div>
      <div className="mt-1.5 h-1.5 w-full rounded-full bg-sunken">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${Math.min(100, percent)}%` }} />
      </div>
      <div className="mt-1 text-xs text-faint">{sub}</div>
    </div>
  );
}

export default function SystemHealthPanel() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    function poll() {
      getSystemHealth()
        .then((h) => {
          if (!cancelled) {
            setHealth(h);
            setError(null);
          }
        })
        .catch(() => !cancelled && setError("Couldn't reach system health endpoint"));
    }
    poll();
    const interval = setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (error) {
    return <div className="rounded-xl border border-border bg-surface p-5 text-sm text-danger shadow-card">{error}</div>;
  }
  if (!health) {
    return <div className="rounded-xl border border-border bg-surface p-5 text-sm text-subtle shadow-card">Loading system health...</div>;
  }

  return (
    <div className="flex flex-col gap-5 rounded-xl border border-border bg-surface p-5 shadow-card">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink">System health</h3>
        <span className="text-xs text-subtle">uptime {formatUptime(health.uptime_seconds)}</span>
      </div>

      <div className="flex flex-col gap-5 sm:flex-row">
        <Meter label="CPU" percent={health.cpu_percent} sub={`${health.cpu_count} cores`} />
        <Meter
          label="RAM"
          percent={health.ram_percent}
          sub={`${health.ram_used_gb} / ${health.ram_total_gb} GB`}
        />
        <Meter
          label="Storage"
          percent={health.disk_percent}
          sub={`${health.disk_used_gb} / ${health.disk_total_gb} GB`}
        />
      </div>

      <div>
        <h4 className="mb-2 text-xs font-medium text-subtle">Network interfaces</h4>
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-border text-subtle">
              <th className="py-1.5 pr-3 font-medium">Name</th>
              <th className="py-1.5 pr-3 font-medium">Status</th>
              <th className="py-1.5 pr-3 font-medium">Speed</th>
              <th className="py-1.5 pr-3 font-medium">Sent</th>
              <th className="py-1.5 font-medium">Received</th>
            </tr>
          </thead>
          <tbody>
            {health.interfaces.map((iface) => (
              <tr key={iface.name} className="border-b border-border last:border-0">
                <td className="py-1.5 pr-3">{iface.name}</td>
                <td className={`py-1.5 pr-3 ${iface.is_up ? "text-success" : "text-faint"}`}>
                  {iface.is_up ? "up" : "down"}
                </td>
                <td className="py-1.5 pr-3">{iface.speed_mbps > 0 ? `${iface.speed_mbps} Mbps` : "-"}</td>
                <td className="py-1.5 pr-3">{formatBytes(iface.bytes_sent)}</td>
                <td className="py-1.5">{formatBytes(iface.bytes_recv)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
