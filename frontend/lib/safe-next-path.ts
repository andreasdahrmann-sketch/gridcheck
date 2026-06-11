const DEFAULT_SAFE_NEXT_PATH = "/projects";

export function isSafeNextPath(value: string): boolean {
  if (!value.startsWith("/") || value.startsWith("//")) return false;
  if (/[\\\u0000-\u001f\u007f]/.test(value)) return false;

  try {
    const parsed = new URL(value, "https://gridcheck.local");
    return parsed.origin === "https://gridcheck.local";
  } catch {
    return false;
  }
}

export function safeNextPath(
  candidate: string | null | undefined,
  fallback: string,
): string {
  const safeFallback = isSafeNextPath(fallback)
    ? fallback
    : DEFAULT_SAFE_NEXT_PATH;
  const trimmed = candidate?.trim();
  if (!trimmed) return safeFallback;
  return isSafeNextPath(trimmed) ? trimmed : safeFallback;
}
