const NOTICE_KEY = "gridcheck_cookie_notice_ack";
const ANALYTICS_KEY = "gridcheck_analytics_consent";

export function hasCookieNoticeAcknowledged(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(NOTICE_KEY) === "1";
  } catch {
    return false;
  }
}

export function acknowledgeCookieNotice(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(NOTICE_KEY, "1");
  } catch {
    /* localStorage unavailable */
  }
}

export function hasAnalyticsConsent(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(ANALYTICS_KEY) === "1";
  } catch {
    return false;
  }
}

export function setAnalyticsConsent(allowed: boolean): void {
  if (typeof window === "undefined") return;
  try {
    if (allowed) {
      localStorage.setItem(ANALYTICS_KEY, "1");
    } else {
      localStorage.removeItem(ANALYTICS_KEY);
    }
  } catch {
    /* localStorage unavailable */
  }
}
