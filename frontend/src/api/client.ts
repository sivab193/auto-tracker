// Minimal fetch-based API client with bearer-token auth.
// Base URL: same-origin by default (dev server proxies /api); overridable via
// VITE_API_BASE_URL for split deployments.

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const TOKEN_KEY = "autotracker_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = getToken();
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

async function handle<T>(res: Response): Promise<T> {
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const body = text ? JSON.parse(text) : undefined;
  if (!res.ok) {
    const detail =
      (body && (body.detail || body.message)) || res.statusText || "Request failed";
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body as T;
}

export const api = {
  async get<T>(path: string): Promise<T> {
    const res = await fetch(`${BASE}${path}`, { headers: authHeaders() });
    return handle<T>(res);
  },
  async post<T>(path: string, data?: unknown): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: data === undefined ? undefined : JSON.stringify(data),
    });
    return handle<T>(res);
  },
  async patch<T>(path: string, data: unknown): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(data),
    });
    return handle<T>(res);
  },
  async del(path: string): Promise<void> {
    const res = await fetch(`${BASE}${path}`, { method: "DELETE", headers: authHeaders() });
    await handle<void>(res);
  },
  async upload<T>(path: string, form: FormData): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: authHeaders(),
      body: form,
    });
    return handle<T>(res);
  },
  downloadUrl(path: string): string {
    return `${BASE}${path}`;
  },
};
