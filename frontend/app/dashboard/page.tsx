"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getMe, Job, listJobs, User } from "@/lib/api";
import { getToken } from "@/lib/auth";
import AppShell from "@/components/AppShell";
import UploadPanel from "@/components/UploadPanel";
import JobsTable from "@/components/JobsTable";

const POLL_MS = 4000;

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshJobs = useCallback(async () => {
    try {
      setJobs(await listJobs());
    } catch {
      // transient poll failure - next tick will retry
    }
  }, []);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    getMe()
      .then(setUser)
      .catch(() => router.replace("/login"));
    refreshJobs();
  }, [router, refreshJobs]);

  useEffect(() => {
    const hasActiveJob = jobs.some((j) => j.status === "pending" || j.status === "processing");
    if (hasActiveJob && !pollRef.current) {
      pollRef.current = setInterval(refreshJobs, POLL_MS);
    }
    if (!hasActiveJob && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobs, refreshJobs]);

  if (!user) {
    return (
      <AppShell breadcrumb="Upload">
        <div className="text-sm text-subtle">Loading...</div>
      </AppShell>
    );
  }

  return (
    <AppShell user={user} breadcrumb="Upload">
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-xl font-semibold text-ink">Upload</h1>
          <p className="mt-0.5 text-sm text-subtle">Read plates from a photo or a video clip.</p>
        </div>
        <UploadPanel role={user.role} onJobCreated={(job) => setJobs((prev) => [job, ...prev])} />
        <div>
          <h2 className="mb-2 text-sm font-semibold text-ink">Video job log</h2>
          <JobsTable jobs={jobs} />
        </div>
      </div>
    </AppShell>
  );
}
