const ANALYTICS_BASE = "/api/backend/api/v1/analytics";

export type ConversionEventName =
  | "page_view_product"
  | "checkout_started"
  | "checkout_completed"
  | "analysis_completed"
  | "report_exported";

export async function trackConversionEvent(
  eventName: ConversionEventName,
  properties: Record<string, unknown> = {},
  sessionId?: string,
): Promise<void> {
  try {
    const res = await fetch(`${ANALYTICS_BASE}/events`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_name: eventName,
        properties,
        ...(sessionId ? { session_id: sessionId } : {}),
      }),
    });
    if (!res.ok) {
      return;
    }
    await res.json().catch(() => undefined);
  } catch {
    // Fire-and-forget: Tracking darf den Produktfluss nicht blockieren.
  }
}
