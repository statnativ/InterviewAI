// Master-admin API client. Deliberately separate from lib/api.ts: this talks
// to /auth/* and /admin/* using a real session cookie (credentials: "include"),
// never the X-Tenant-Id/X-User-Email dev headers the rest of the app uses.

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export interface AdminTenant {
  id: string;
  name: string;
  slug: string;
  createdAt: string;
}

export interface AdminUser {
  id: string;
  tenantId: string;
  tenantName: string;
  email: string;
  name: string | null;
  role: string;
  status: "pending" | "active" | "disabled";
  createdAt: string;
}

export interface AdminPracticeTest {
  id: string;
  tenantId: string;
  tenantName: string;
  title: string;
  mode: string;
  status: string;
  questions: unknown[];
  duration: number;
  createdAt: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const adminApi = {
  login: (username: string, password: string) =>
    request<{ username: string; name: string | null; role: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  me: () => request<{ username: string; name: string | null; role: string }>("/auth/me"),

  listTenants: () => request<AdminTenant[]>("/admin/tenants"),
  createTenant: (input: { name: string; slug: string }) =>
    request<AdminTenant>("/admin/tenants", { method: "POST", body: JSON.stringify(input) }),

  listUsers: () => request<AdminUser[]>("/admin/users"),
  createUser: (input: { tenantId: string; email: string; name?: string; role: string; password: string }) =>
    request<AdminUser>("/admin/users", { method: "POST", body: JSON.stringify(input) }),
  approveUser: (id: string) => request<AdminUser>(`/admin/users/${id}/approve`, { method: "POST" }),
  disableUser: (id: string) => request<AdminUser>(`/admin/users/${id}/disable`, { method: "POST" }),

  listPracticeTests: () => request<AdminPracticeTest[]>("/admin/practice-tests"),
  createPracticeTest: (input: { tenantId: string; title: string; mode: string; duration: number }) =>
    request<AdminPracticeTest>("/admin/practice-tests", { method: "POST", body: JSON.stringify(input) }),
};
