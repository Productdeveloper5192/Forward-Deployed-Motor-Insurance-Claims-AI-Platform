import type {
  AuditLogOut,
  ClaimOut,
  EvaluationMetrics,
  NotificationOut,
  PolicyOut,
  TokenResponse,
  UserOut,
  UserRole,
  WorkflowRunOut,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let token: string | null = localStorage.getItem("motoclaims_token");

export function setToken(next: string | null) {
  token = next;
  if (next) localStorage.setItem("motoclaims_token", next);
  else localStorage.removeItem("motoclaims_token");
}

export function getToken() {
  return token;
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; isForm?: boolean; query?: Record<string, string | number | undefined> } = {}
): Promise<T> {
  const { method = "GET", body, isForm = false, query } = options;

  let url = `${BASE_URL}${path}`;
  if (query) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== "") params.set(key, String(value));
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }

  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";

  const resp = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
  });

  if (!resp.ok) {
    let message = resp.statusText;
    try {
      const data = await resp.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      /* body wasn't JSON */
    }
    throw new ApiError(resp.status, message);
  }

  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string, full_name: string) =>
    request<TokenResponse>("/auth/register", { method: "POST", body: { email, password, full_name } }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: { email, password } }),

  me: () => request<UserOut>("/auth/me"),

  createClaim: (payload: {
    policy_number: string;
    incident_date: string;
    incident_description: string;
    incident_location: string;
  }) => request<ClaimOut>("/claims", { method: "POST", body: payload }),

  listClaims: () => request<ClaimOut[]>("/claims"),

  getClaim: (id: number) => request<ClaimOut>(`/claims/${id}`),

  uploadDocument: (claimId: number, docType: string, file: File) => {
    const form = new FormData();
    form.append("doc_type", docType);
    form.append("file", file);
    return request<ClaimOut>(`/claims/${claimId}/documents`, { method: "POST", body: form, isForm: true });
  },

  submitClaim: (claimId: number) => request<ClaimOut>(`/claims/${claimId}/submit`, { method: "POST" }),

  getWorkflow: (claimId: number) => request<WorkflowRunOut[]>(`/claims/${claimId}/workflow`),

  payClaim: (claimId: number) => request<ClaimOut>(`/claims/${claimId}/pay`, { method: "POST" }),

  reviewQueue: () => request<ClaimOut[]>("/review/queue"),

  submitDecision: (claimId: number, decision: "approved" | "denied", approved_amount: number | null, notes: string) =>
    request<ClaimOut>(`/review/${claimId}/decision`, {
      method: "POST",
      body: { decision, approved_amount, notes },
    }),

  createPolicy: (payload: Omit<PolicyOut, "id">) => request<PolicyOut>("/admin/policies", { method: "POST", body: payload }),

  listPolicies: () => request<PolicyOut[]>("/admin/policies"),

  evaluation: () => request<EvaluationMetrics>("/admin/evaluation"),

  auditLog: (claimId?: number) => request<AuditLogOut[]>("/admin/audit-log", { query: { claim_id: claimId } }),

  listUsers: () => request<UserOut[]>("/admin/users"),

  createStaffUser: (email: string, password: string, full_name: string, role: UserRole) =>
    request<UserOut>("/admin/users", { method: "POST", body: { email, password, full_name, role } }),

  notifications: () => request<NotificationOut[]>("/notifications"),

  markNotificationRead: (id: number) => request<NotificationOut>(`/notifications/${id}/read`, { method: "POST" }),
};
