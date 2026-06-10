const DEFAULT_AUTH_REDIRECT = "/projects";
const SAFE_ORIGIN = "https://gridcheck.local";

function isSafeAppPath(value: string): boolean {
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return false;
  }
  if (/[\u0000-\u001F\u007F]/.test(value)) {
    return false;
  }
  try {
    const parsed = new URL(value, SAFE_ORIGIN);
    return parsed.origin === SAFE_ORIGIN && parsed.pathname.startsWith("/");
  } catch {
    return false;
  }
}

export function sanitizeAppRedirect(rawTarget: string | null | undefined, fallback: string): string {
  const safeFallback = isSafeAppPath(fallback) ? fallback : DEFAULT_AUTH_REDIRECT;
  const target = rawTarget?.trim();
  if (!target) return safeFallback;
  return isSafeAppPath(target) ? target : safeFallback;
}
