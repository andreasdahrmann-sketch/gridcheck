const ACCESS_TOKEN_KEY = "gridcheck_access_token";

export function setAccessToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
  } else {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function bearerAuthHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function readNonEmptyString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

/** Maps FastAPI, gateway (Railway/Vercel) and proxy error JSON to a user-facing message. */
export function extractApiErrorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;

  const record = body as Record<string, unknown>;

  const topLevelMessage = readNonEmptyString(record.message);
  if (topLevelMessage) return topLevelMessage;

  const topLevelError = readNonEmptyString(record.error);
  if (topLevelError) return topLevelError;

  if (record.error && typeof record.error === "object" && !Array.isArray(record.error)) {
    const nestedMessage = readNonEmptyString((record.error as { message?: unknown }).message);
    if (nestedMessage) return nestedMessage;
  }

  const detail = record.detail;
  const detailString = readNonEmptyString(detail);
  if (detailString) return detailString;

  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const detailRecord = detail as Record<string, unknown>;
    const message = readNonEmptyString(detailRecord.message);
    if (message) return message;
    const hint = readNonEmptyString(detailRecord.hint);
    if (hint) return hint;
    const code = readNonEmptyString(detailRecord.code);
    if (code) return code.replace(/_/g, " ");
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (first && typeof first === "object" && "msg" in first) {
      const msg = readNonEmptyString((first as { msg?: unknown }).msg);
      if (msg) return msg;
    }
  }

  return fallback;
}
