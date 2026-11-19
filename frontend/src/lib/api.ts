import type {
  AdminJobResponse,
  AdminStatusResponse,
  DashboardPayload,
} from "./types";

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // ignore non-json error body
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export const IS_DEMO = import.meta.env.MODE === "demo";

export function fetchDashboard(): Promise<DashboardPayload> {
  if (IS_DEMO) {
    return requestJson<DashboardPayload>(`${import.meta.env.BASE_URL}demo-data/dashboard.json`);
  }
  return requestJson<DashboardPayload>("/api/dashboard");
}

export function fetchAdminStatus(): Promise<AdminStatusResponse> {
  return requestJson<AdminStatusResponse>("/api/admin/status");
}

export function adminLogin(password: string): Promise<AdminStatusResponse> {
  return requestJson<AdminStatusResponse>("/api/admin/login", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

export function adminLogout(): Promise<AdminStatusResponse> {
  return requestJson<AdminStatusResponse>("/api/admin/logout", {
    method: "POST",
  });
}

export function runCollector(): Promise<AdminJobResponse> {
  return requestJson<AdminJobResponse>("/api/admin/run/collector", {
    method: "POST",
  });
}

export function runProcessor(): Promise<AdminJobResponse> {
  return requestJson<AdminJobResponse>("/api/admin/run/processor", {
    method: "POST",
  });
}

export function clearDashboardCache(): Promise<{ ok: boolean }> {
  return requestJson<{ ok: boolean }>("/api/admin/clear-cache", {
    method: "POST",
  });
}
