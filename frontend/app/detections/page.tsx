"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getMe, User } from "@/lib/api";
import { getToken } from "@/lib/auth";
import AppShell from "@/components/AppShell";
import DetectionsTable from "@/components/DetectionsTable";

export default function DetectionsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    getMe()
      .then(setUser)
      .catch(() => router.replace("/login"));
  }, [router]);

  if (!user) {
    return (
      <AppShell breadcrumb="Detections">
        <div className="text-sm text-subtle">Loading...</div>
      </AppShell>
    );
  }

  return (
    <AppShell user={user} breadcrumb="Detections">
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-xl font-semibold text-ink">Recent detections</h1>
          <p className="mt-0.5 text-sm text-subtle">
            {user.role.is_admin
              ? "Every user's readings by default - toggle \u201Conly my detections\u201D to scope to yourself."
              : "Every plate matched from your photo and video uploads."}
          </p>
        </div>
        <DetectionsTable role={user.role} selfId={user.id} />
      </div>
    </AppShell>
  );
}
