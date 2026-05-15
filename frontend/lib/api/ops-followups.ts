import { getCsrfTokenFromCookie } from "@/lib/api/csrf";

export type OpsFollowup = {
  entitlement_id: number;
  offer_id: string;
  package_scope: string;
  status: string;
  ops_status: string;
  express_requested: boolean;
  checkout_session_id?: string | null;
  remaining_credits?: number | null;
  customer_user_id: number;
  customer_email?: string | null;
  customer_name?: string | null;
  project_name?: string | null;
  analysis_run_id?: number | null;
  analysis_created_at?: string | null;
  ops_assignee_user_id?: number | null;
  ops_assignee_email?: string | null;
  ops_assignee_name?: string | null;
  ops_assigned_at?: string | null;
  ops_started_at?: string | null;
  ops_completed_at?: string | null;
  ops_last_comment?: string | null;
  updated_at?: string | null;
  next_action: string;
};

const BASE = "/api/backend/api/v1/ops-followups";

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail?.message ?? "API request failed");
  }
  return res.json() as Promise<T>;
}

export async function listOpsFollowups(options?: { includeCompleted?: boolean; assignedToMe?: boolean; limit?: number }) {
  const params = new URLSearchParams();
  if (options?.includeCompleted) params.set("include_completed", "true");
  if (options?.assignedToMe) params.set("assigned_to_me", "true");
  if (options?.limit) params.set("limit", String(options.limit));
  const query = params.toString();
  const res = await fetch(`${BASE}${query ? `?${query}` : ""}`, {
    credentials: "include",
    cache: "no-store",
  });
  return parse<OpsFollowup[]>(res);
}

export async function claimOpsFollowup(entitlementId: number, comment?: string) {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(`${BASE}/${entitlementId}/claim`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(csrf ? { "X-CSRF-Token": csrf } : {}) },
    body: JSON.stringify({ comment: comment || null }),
  });
  return parse<OpsFollowup>(res);
}

export async function updateOpsFollowupStatus(entitlementId: number, status: "in_progress" | "completed", comment?: string) {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(`${BASE}/${entitlementId}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(csrf ? { "X-CSRF-Token": csrf } : {}) },
    body: JSON.stringify({ status, comment: comment || null }),
  });
  return parse<OpsFollowup>(res);
}
