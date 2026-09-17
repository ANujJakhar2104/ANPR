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

// Roles are admin-managed data now, not a fixed basic/pro/admin enum - an
// admin can rename them or add new ones with their own capability flags.
export type RoleInfo = {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  can_use_video: boolean;
  is_admin: boolean;
  is_default: boolean;
  is_system: boolean;
};

export type User = {
  id: string;
  email: string;
  username: string;
  role: RoleInfo;
  is_active: boolean;
  created_at: string;
};

export type PasswordPolicy = {
  min_length: number;
  max_length: number;
  require_uppercase: boolean;
  require_lowercase: boolean;
  require_digit: boolean;
  require_special: boolean;
  block_common_passwords: boolean;
  block_username_in_password: boolean;
};

export type CharAnalysisEntry = {
  position: number;
  raw_char: string;
  corrected_char: string;
  expected_type: "letter" | "digit";
  was_corrected: boolean;
};

export type Detection = {
  car_id: number;
  car_bbox: number[];
  license_plate_bbox: number[];
  license_plate_bbox_score: number;
  license_number: string | null;
  license_number_score: number | null;
  raw_ocr_text: string | null;
  char_analysis: CharAnalysisEntry[] | null;
};

// A persisted row from the `detections` table - what the Recent Detections
// view lists, as opposed to `Detection` above which is a single synchronous
// /detect/image response that hasn't necessarily been saved to disk yet.
export type DetectionRecord = {
  id: string;
  user_id: string;
  job_id: string | null;
  source: "image" | "video";
  car_id: string;
  license_number: string | null;
  license_number_score: string | null;
  raw_ocr_text: string | null;
  char_analysis: CharAnalysisEntry[] | null;
  created_at: string;
};

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type DetectionFilters = {
  source?: "image" | "video";
  plate?: string;
  date_from?: string;
  date_to?: string;
  user_id?: string;
  page?: number;
  page_size?: number;
};

export type AuditLogEntry = {
  id: string;
  timestamp: string;
  user_id: string | null;
  username: string | null;
  action: string;
  status: "success" | "failure";
  detail: string | null;
  ip_address: string | null;
};

export type AuditLogFilters = {
  action?: string;
  status?: string;
  username?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
};

export type SystemHealth = {
  cpu_percent: number;
  cpu_count: number;
  ram_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  interfaces: { name: string; is_up: boolean; speed_mbps: number; bytes_sent: number; bytes_recv: number }[];
  uptime_seconds: number;
};

export type AdminSummary = {
  total_users: number;
  users_by_role: Record<string, number>;
  total_detections: number;
  detections_last_24h: number;
  total_video_jobs: number;
  jobs_pending_or_processing: number;
  jobs_failed: number;
};

function toQuery(params: Record<string, string | number | undefined>): string {
  const usable = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (usable.length === 0) return "";
  return "?" + usable.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join("&");
}

async function downloadBlob(path: string, suggestedName: string): Promise<void> {
  const res = await request(path);
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

// Public (no auth) - lets the register page show live password rules
// before the person has an account. Same data as GET /admin/password-policy.
export async function getPublicPasswordPolicy(): Promise<PasswordPolicy> {
  const res = await request("/auth/password-policy");
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
  return downloadBlob(`/detect/jobs/${jobId}/download`, suggestedName);
}

// --- recent detections -------------------------------------------------

export async function listDetections(filters: DetectionFilters): Promise<Page<DetectionRecord>> {
  const res = await request(`/detect/detections${toQuery(filters)}`);
  return res.json();
}

export async function exportDetections(format: "csv" | "html" | "pdf", filters: DetectionFilters): Promise<void> {
  const { page, page_size, ...rest } = filters;
  return downloadBlob(`/detect/detections/export/${format}${toQuery(rest)}`, `detections.${format}`);
}

// --- admin: system health, summary, users, audit log --------------------

export async function getSystemHealth(): Promise<SystemHealth> {
  const res = await request("/admin/system-health");
  return res.json();
}

export async function getAdminSummary(): Promise<AdminSummary> {
  const res = await request("/admin/summary");
  return res.json();
}

export async function listUsers(): Promise<User[]> {
  const res = await request("/admin/users");
  return res.json();
}

export async function updateUserRole(userId: string, roleId: string): Promise<User> {
  const res = await request(`/admin/users/${userId}/role`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role_id: roleId }),
  });
  return res.json();
}

// --- admin: roles (create/rename/delete custom roles) ---------------------

export async function listRoles(): Promise<RoleInfo[]> {
  const res = await request("/admin/roles");
  return res.json();
}

export async function createRole(payload: {
  name: string;
  display_name: string;
  description?: string;
  can_use_video?: boolean;
  is_admin?: boolean;
  is_default?: boolean;
}): Promise<RoleInfo> {
  const res = await request("/admin/roles", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function updateRole(roleId: string, payload: Partial<Omit<RoleInfo, "id" | "name" | "is_system">>): Promise<RoleInfo> {
  const res = await request(`/admin/roles/${roleId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function deleteRole(roleId: string): Promise<void> {
  await request(`/admin/roles/${roleId}`, { method: "DELETE" });
}

// --- admin: password policy -------------------------------------------

export async function getPasswordPolicy(): Promise<PasswordPolicy> {
  const res = await request("/admin/password-policy");
  return res.json();
}

export async function updatePasswordPolicy(payload: Partial<PasswordPolicy>): Promise<PasswordPolicy> {
  const res = await request("/admin/password-policy", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function listAuditLogs(filters: AuditLogFilters): Promise<Page<AuditLogEntry>> {
  const res = await request(`/admin/audit-logs${toQuery(filters)}`);
  return res.json();
}

export async function exportAuditLogs(format: "csv" | "html" | "pdf", filters: AuditLogFilters): Promise<void> {
  const { page, page_size, ...rest } = filters;
  return downloadBlob(`/admin/audit-logs/export/${format}${toQuery(rest)}`, `audit-log.${format}`);
}
