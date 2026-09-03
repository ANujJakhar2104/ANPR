"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, login } from "@/lib/api";
import { saveToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const token = await login(identifier, password);
      saveToken(token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-asphalt px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-xl font-semibold text-ink">ANPR Console</h1>
          <p className="mt-1 text-sm text-muted">Sign in to read plates.</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 border border-hairline bg-panel p-6">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="identifier" className="text-sm text-muted">
              Email or username
            </label>
            <input
              id="identifier"
              type="text"
              required
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              className="border border-hairline bg-asphalt px-3 py-2 text-sm text-ink outline-none focus:border-amber"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="password" className="text-sm text-muted">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="border border-hairline bg-asphalt px-3 py-2 text-sm text-ink outline-none focus:border-amber"
            />
          </div>

          {error && <p className="text-sm text-danger">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="mt-2 border border-amber py-2 text-sm font-medium text-amber transition-colors hover:bg-amber hover:text-asphalt disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-muted">
          No account?{" "}
          <Link href="/register" className="text-amber hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </main>
  );
}
