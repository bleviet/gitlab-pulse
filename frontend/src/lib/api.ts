import type {
  AdminJobResponse,
  AdminStatusResponse,
  DashboardPayload,
  RuleDeleteResponse,
  RuleProblem,
  RulePreviewResponse,
  RuleSaveResponse,
  RuleSetBody,
  RuleSetsResponse,
  RuleTextResponse,
  RuleVersionResponse,
  RuleVersionsResponse,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly problems: RuleProblem[];

  constructor(message: string, status: number, problems: RuleProblem[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.problems = problems;
  }
}

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
    let message = `Request failed (${response.status})`;
    let problems: RuleProblem[] = [];
    try {
      const body = (await response.json()) as {
        detail?: string | { message?: string; problems?: RuleProblem[] };
      };
      if (typeof body.detail === "string" && body.detail) {
        message = body.detail;
      } else if (body.detail && typeof body.detail === "object") {
        if (body.detail.message) message = body.detail.message;
        if (Array.isArray(body.detail.problems)) problems = body.detail.problems;
      }
    } catch {
      // ignore non-json error body
    }
    throw new ApiError(message, response.status, problems);
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

export function fetchRules(): Promise<RuleSetsResponse> {
  return requestJson<RuleSetsResponse>("/api/rules");
}

export function saveRuleSet(
  name: string,
  revision: string,
  rule: RuleSetBody,
): Promise<RuleSaveResponse> {
  return requestJson<RuleSaveResponse>(`/api/admin/rules/${encodeURIComponent(name)}`, {
    method: "PUT",
    body: JSON.stringify({ revision, rule }),
  });
}

export function previewRuleSet(
  name: string,
  rule: RuleSetBody,
  signal?: AbortSignal,
): Promise<RulePreviewResponse> {
  return requestJson<RulePreviewResponse>(
    `/api/admin/rules/${encodeURIComponent(name)}/preview`,
    { method: "POST", body: JSON.stringify({ rule }), signal },
  );
}

export function createRuleSet(rule: RuleSetBody): Promise<RuleSaveResponse> {
  return requestJson<RuleSaveResponse>("/api/admin/rules", {
    method: "POST",
    body: JSON.stringify({ rule }),
  });
}

export function deleteRuleSet(name: string, revision: string): Promise<RuleDeleteResponse> {
  return requestJson<RuleDeleteResponse>(
    `/api/admin/rules/${encodeURIComponent(name)}?revision=${encodeURIComponent(revision)}`,
    { method: "DELETE" },
  );
}

export function fetchRuleVersions(name: string): Promise<RuleVersionsResponse> {
  return requestJson<RuleVersionsResponse>(
    `/api/admin/rules/${encodeURIComponent(name)}/versions`,
  );
}

export function fetchRuleVersion(name: string, id: string): Promise<RuleVersionResponse> {
  return requestJson<RuleVersionResponse>(
    `/api/admin/rules/${encodeURIComponent(name)}/versions/${encodeURIComponent(id)}`,
  );
}

export function fetchRuleText(name: string): Promise<RuleTextResponse> {
  return requestJson<RuleTextResponse>(`/api/rules/${encodeURIComponent(name)}/text`);
}
