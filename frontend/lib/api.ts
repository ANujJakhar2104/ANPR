import { clearToken, getToken } from "./auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON - fall back to statusText
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res;
}

export type User = {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
};

export type Detection = {
  car_id: number;
  car_bbox: number[];
  license_plate_bbox: number[];
  license_plate_bbox_score: number;
  license_number: string | null;
  license_number_score: number | null;
};

export type Job = {
  id: string;
  status: "pending" | "processing" | "completed" | "failed";
  input_filename: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export async function register(email: string, username: string, password: string): Promise<User> {
  const res = await request("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, username, password }),
  });
  return res.json();
}

export async function login(identifier: string, password: string): Promise<string> {
  const form = new URLSearchParams();
  form.set("username", identifier);
  form.set("password", password);
  const res = await request("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  const data = await res.json();
  return data.access_token as string;
}

export async function getMe(): Promise<User> {
  const res = await request("/auth/me");
  return res.json();
}

export async function detectImage(file: File): Promise<{ detections: Detection[]; annotated_image_base64: string }> {
  const form = new FormData();
  form.set("file", file);
  const res = await request("/detect/image", { method: "POST", body: form });
  return res.json();
}

export async function detectVideo(file: File): Promise<Job> {
  const form = new FormData();
  form.set("file", file);
  const res = await request("/detect/video", { method: "POST", body: form });
  return res.json();
}

export async function listJobs(): Promise<Job[]> {
  const res = await request("/detect/jobs");
  return res.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await request(`/detect/jobs/${jobId}`);
  return res.json();
}

// Downloads go through fetch (not a plain <a href>) so the JWT can travel in
// the Authorization header rather than sitting in a URL where it could end
// up in browser history or server access logs.
export async function downloadJob(jobId: string, suggestedName: string): Promise<void> {
  const res = await request(`/detect/jobs/${jobId}/download`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = suggestedName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
