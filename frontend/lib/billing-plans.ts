/**
 * Public pricing tier ids (URL ?plan=) mapped to backend Stripe offer_ids.
 */
export const CHECKOUT_PLAN_TO_OFFER: Record<string, string> = {
  free: "free",
  basic: "basic_schnellcheck",
  premium: "premium_pre_check",
  professional: "professional_anschlussstrategie",
  pro: "pro_lizenz",
  express: "express_upgrade",
};

const SELF_SERVE_CHECKOUT_PLANS = new Set(["basic", "premium", "professional", "pro"]);

export function normalizeCheckoutPlan(raw?: string | null): string | null {
  if (!raw) return null;
  const key = raw.trim().toLowerCase();
  return key in CHECKOUT_PLAN_TO_OFFER ? key : null;
}

export function offerIdForCheckoutPlan(plan: string): string | null {
  return CHECKOUT_PLAN_TO_OFFER[plan] ?? null;
}

export function isSelfServeCheckoutPlan(plan: string): boolean {
  return SELF_SERVE_CHECKOUT_PLANS.has(plan);
}

export function registerHrefForPlan(plan: string, next = "/settings"): string {
  return `/register?plan=${encodeURIComponent(plan)}&next=${encodeURIComponent(next)}`;
}

export function loginHrefForPlan(plan: string, next = "/settings"): string {
  return `/login?plan=${encodeURIComponent(plan)}&next=${encodeURIComponent(next)}`;
}

export function settingsCheckoutHref(plan: string): string {
  return `/settings?plan=${encodeURIComponent(plan)}&checkout=1`;
}
