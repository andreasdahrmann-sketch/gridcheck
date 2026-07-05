const SAFE_NEXT_BASE = "https://gridcheck.local";

export function safeNextPath(raw: string | null | undefined, fallback: string): string {
  const value = raw?.trim();
  if (!value) return fallback;
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return fallback;
  }

  try {
    const parsed = new URL(value, SAFE_NEXT_BASE);
    if (parsed.origin !== SAFE_NEXT_BASE) return fallback;
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return fallback;
  }
}
