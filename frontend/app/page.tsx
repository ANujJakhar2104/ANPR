"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getStoredIsAdmin, getToken } from "@/lib/auth";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    router.replace(getStoredIsAdmin() ? "/admin" : "/dashboard");
  }, [router]);

  return null;
}
