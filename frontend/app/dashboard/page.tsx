"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getMe, Job, listJobs, User } from "@/lib/api";
import { getToken } from "@/lib/auth";
import TopBar from "@/components/TopBar";
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
      <main className="min-h-screen bg-asphalt">
        <TopBar />
        <div className="mx-auto max-w-5xl px-6 py-10 text-sm text-muted">Loading...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-asphalt">
      <TopBar username={user.username} />
      <div className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-8">
        <UploadPanel onJobCreated={(job) => setJobs((prev) => [job, ...prev])} />
        <div>
          <h2 className="mb-2 text-sm text-muted">Video job log</h2>
          <JobsTable jobs={jobs} />
        </div>
      </div>
    </main>
  );
}
