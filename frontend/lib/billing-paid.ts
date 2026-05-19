import type { BillingStatus } from "@/lib/api/billing";

/** True when the user is on a paid tier (Pro, credits, or non-free plan). */
export function isPaidBillingStatus(status: BillingStatus | null | undefined): boolean {
  if (!status) return false;
  if (status.plan_tier && status.plan_tier !== "free") return true;
  if (status.has_active_subscription) return true;
  if (status.has_prepaid_credits) return true;
  if (status.active_paid_entitlements_count > 0) return true;
  return false;
}
