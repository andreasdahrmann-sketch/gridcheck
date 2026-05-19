import { getCsrfTokenFromCookie } from "@/lib/api/csrf";
import { bearerAuthHeaders } from "@/lib/api/session";

export type BillingOffer = {
  offer_id: string;
  name: string;
  category: string;
  billing_mode: string;
  price_label: string;
  amount_cents?: number | null;
  interval?: string | null;
  tagline: string;
  summary: string;
  cta_label: string;
  checkout_enabled: boolean;
  stripe_price_id?: string | null;
  recommended_for?: string | null;
  featured?: boolean;
  self_serve_unlock?: boolean;
  visibility?: string;
};

export type BillingCatalog = {
  headline: string;
  subheadline: string;
  offers: BillingOffer[];
  addons: BillingOffer[];
};

export type BillingStatus = {
  plan_tier: string;
  billing_status: string;
  has_active_subscription: boolean;
  subscription_state: string;
  billing_attention?: BillingAttention | null;
  stripe_configured: boolean;
  customer_portal_available: boolean;
  has_prepaid_credits: boolean;
  active_paid_entitlements_count: number;
  has_ops_pending: boolean;
  open_ops_followups_count: number;
  billing_state_label: string;
  free_checks_limit: number;
  free_checks_used: number;
  free_checks_remaining: number;
  can_run_analysis: boolean;
  upgrade_required: boolean;
  current_period_end?: string | null;
  stripe_customer_id?: string | null;
  catalog: BillingCatalog;
  recommended_offer_ids: string[];
  active_entitlements: BillingEntitlement[];
  entitlement_history: BillingEntitlementHistoryItem[];
  ops_followups: BillingOpsFollowup[];
  recent_billing_events: BillingEvent[];
  stripe_readiness: StripeReadiness;
  analysis_options: BillingAnalysisOption[];
  usage_policy: {
    free_checks: { limit: number; consumption_rule: string };
    pay_per_use: { consumption_rule: string };
    subscription: { offer_id: string; included_credits_per_period: number; consumption_rule: string };
    ops_boundary: { professional: string; express: string };
  };
};

export type AnalysisHistoryItem = {
  id: number;
  project_id?: number | null;
  project_name?: string | null;
  source: string;
  status: string;
  score?: number | null;
  decision_code?: string | null;
  revision_hash?: string | null;
  offer_id?: string | null;
  package_scope: string;
  usage_bucket: string;
  entitlement_id?: number | null;
  billing_category: string;
  free_quota_consumed: boolean;
  created_at: string;
};

export type BillingEntitlement = {
  id: number;
  offer_id: string;
  offer_category: string;
  package_scope: string;
  status: string;
  source: string;
  total_credits?: number | null;
  used_credits: number;
  remaining_credits?: number | null;
  valid_from?: string | null;
  valid_until?: string | null;
  checkout_session_id?: string | null;
  stripe_subscription_id?: string | null;
  express_requested: boolean;
  ops_followup_required: boolean;
  ops_status: string;
  metadata?: Record<string, unknown>;
};

export type BillingEntitlementHistoryItem = BillingEntitlement & {
  last_analysis_run_id?: number | null;
  last_analysis_created_at?: string | null;
  last_analysis_project_name?: string | null;
  last_analysis_score?: number | null;
  last_analysis_decision_code?: string | null;
};

export type BillingAttention = {
  severity: string;
  title: string;
  message: string;
  action: string;
  cta_label?: string | null;
};

export type BillingEvent = {
  id: number;
  event_type: string;
  status: string;
  provider_event_id?: string | null;
  checkout_session_id?: string | null;
  provider_customer_id?: string | null;
  provider_subscription_id?: string | null;
  amount_cents?: number | null;
  currency?: string | null;
  created_at?: string | null;
};

export type BillingOpsFollowup = {
  entitlement_id: number;
  offer_id: string;
  package_scope: string;
  status: string;
  ops_status: string;
  express_requested: boolean;
  checkout_session_id?: string | null;
  remaining_credits?: number | null;
  project_name?: string | null;
  analysis_run_id?: number | null;
  analysis_created_at?: string | null;
  updated_at?: string | null;
  next_action: string;
};

export type StripeReadiness = {
  status: string;
  checkout_ready: boolean;
  webhook_ready: boolean;
  portal_ready: boolean;
  issues: string[];
  warnings: string[];
  offers: Array<{
    offer_id: string;
    billing_mode: string;
    ready: boolean;
    issues: string[];
  }>;
};

export type BillingAnalysisOption = {
  offer_id: string;
  label: string;
  package_scope: string;
  remaining_credits?: number | null;
  usage_bucket: string;
  report_scope: string;
  feature_flags?: Record<string, boolean>;
  default?: boolean;
  ops_followup_required?: boolean;
};

export type BillingCheckoutSessionStatus = {
  session_id?: string | null;
  offer_id?: string | null;
  offer_name?: string | null;
  session_status?: string | null;
  payment_status?: string | null;
  synced: boolean;
  checkout_url?: string | null;
  billing: BillingStatus;
};

const BILLING_BASE = "/api/backend/api/v1/billing";
const ANALYSIS_BASE = "/api/backend/api/v1/analysis";

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail?.message ?? "API request failed");
  }
  return res.json() as Promise<T>;
}

export async function getBillingStatus() {
  const res = await fetch(`${BILLING_BASE}/status`, {
    credentials: "include",
    cache: "no-store",
    headers: { ...bearerAuthHeaders() },
  });
  return parse<BillingStatus>(res);
}

export async function createBillingCheckout(offerId = "pro_lizenz") {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(`${BILLING_BASE}/checkout`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...bearerAuthHeaders(),
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    body: JSON.stringify({ offer_id: offerId }),
  });
  return parse<{ url: string; session_id?: string | null; offer_id?: string | null; offer_name?: string | null }>(res);
}

export async function createBillingPortal() {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(`${BILLING_BASE}/portal`, {
    method: "POST",
    credentials: "include",
    headers: {
      ...bearerAuthHeaders(),
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
  });
  return parse<{ url: string }>(res);
}

export async function getBillingCheckoutSessionStatus(sessionId: string) {
  const res = await fetch(`${BILLING_BASE}/checkout-session?session_id=${encodeURIComponent(sessionId)}`, {
    credentials: "include",
    cache: "no-store",
    headers: { ...bearerAuthHeaders() },
  });
  return parse<BillingCheckoutSessionStatus>(res);
}

export async function listAnalysisHistory(limit = 20) {
  const res = await fetch(`${ANALYSIS_BASE}/history?limit=${limit}`, {
    credentials: "include",
    cache: "no-store",
    headers: { ...bearerAuthHeaders() },
  });
  return parse<AnalysisHistoryItem[]>(res);
}

export async function getBillingCatalog() {
  const res = await fetch(`${BILLING_BASE}/catalog`, {
    cache: "no-store",
  });
  return parse<BillingCatalog>(res);
}
