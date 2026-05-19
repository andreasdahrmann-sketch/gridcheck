import { getCsrfTokenFromCookie } from "@/lib/api/csrf";
import { bearerAuthHeaders, extractApiErrorMessage, setAccessToken } from "@/lib/api/session";

export type AuthUser = {
  id: number;
  email: string;
  role: string;
  full_name?: string | null;
  vnb_verification_status?: "none" | "pending" | "approved";
  netzbetreiber_verified?: boolean;
  vnb_dashboard_access?: boolean;
};

type TokenResponse = {
  access_token: string;
  refresh_token?: string;
  token_type: string;
};

/** Prefer server route handlers; fallback to rewrite if deploy has no app/api/auth yet. */
const AUTH_BASE = "/api/auth";
const AUTH_REWRITE_BASE = "/api/backend/api/v1/auth";

const BACKEND_UNREACHABLE_HINT =
  "Backend nicht erreichbar. Vercel: BACKEND_URL=https://gridcheck-production.up.railway.app setzen (nur Origin), dann Redeploy. Railway: GET /health pruefen. Lokal: uvicorn auf Port 8000.";

const BACKEND_URL_MISSING_HINT =
  "BACKEND_URL fehlt auf Vercel. In Project Settings setzen: BACKEND_URL=https://gridcheck-production.up.railway.app (nur Origin, ohne /api/v1), dann Redeploy.";

function readDetailCode(body: unknown): string | null {
  if (!body || typeof body !== "object" || !("detail" in body)) return null;
  const detail = (body as { detail?: unknown }).detail;
  if (detail && typeof detail === "object" && "code" in detail) {
    const code = (detail as { code?: unknown }).code;
    return typeof code === "string" ? code : null;
  }
  return null;
}

async function readResponseBody(res: Response): Promise<unknown> {
  const contentType = res.headers.get("content-type") ?? "";
  const text = await res.text().catch(() => "");

  if (contentType.includes("application/json")) {
    if (!text) return {};
    try {
      return JSON.parse(text) as unknown;
    } catch {
      return {
        detail: {
          message: `Ungueltige JSON-Antwort (HTTP ${res.status})`,
          hint: text.slice(0, 200),
        },
      };
    }
  }

  if (!text) return {};
  return {
    detail: {
      message: `Unerwartete Antwort vom Server (HTTP ${res.status})`,
      hint: text.slice(0, 200),
    },
  };
}

function resolveAuthErrorMessage(res: Response, body: unknown): string {
  const code = readDetailCode(body);
  const parsed = extractApiErrorMessage(body, "");

  if (code === "BACKEND_URL_MISSING") return BACKEND_URL_MISSING_HINT;
  if (code === "BACKEND_UNREACHABLE") return BACKEND_UNREACHABLE_HINT;
  if (code === "LOGIN_INVALID") {
    return parsed || "E-Mail oder Passwort ist falsch.";
  }
  if (code === "EMAIL_EXISTS") {
    return parsed || "Diese E-Mail ist bereits registriert. Bitte einloggen oder eine andere E-Mail verwenden.";
  }
  if (code === "PASSWORD_TOO_WEAK") {
    return parsed || "Passwort erfuellt die Mindestanforderungen nicht.";
  }
  if (code === "USER_INACTIVE") {
    return parsed || "Ihr Konto ist deaktiviert. Bitte den Administrator kontaktieren.";
  }
  if (code === "AUTH_JWT_NOT_CONFIGURED") {
    return (
      parsed ||
      "JWT-Signatur ist auf dem Backend nicht konfiguriert. Railway: JWT_SECRET und JWT_REFRESH_SECRET setzen (je min. 32 Zeichen, unterschiedliche Werte), APP_ENV=production, dann Redeploy."
    );
  }
  if (code === "DATABASE_SCHEMA_MISSING" || code === "DATABASE_UNAVAILABLE") {
    const detail =
      body &&
      typeof body === "object" &&
      "detail" in body &&
      body.detail &&
      typeof body.detail === "object" &&
      !Array.isArray(body.detail)
        ? (body.detail as { message?: unknown; hint?: unknown })
        : null;
    const message =
      typeof detail?.message === "string" && detail.message.trim()
        ? detail.message.trim()
        : parsed || "Datenbank nicht erreichbar oder Schema nicht migriert.";
    const hint = typeof detail?.hint === "string" ? detail.hint.trim() : "";
    if (hint && !message.includes(hint)) return `${message} ${hint}`;
    return message;
  }
  if (parsed) return parsed;

  if (res.status === 503) {
    return "Datenbank nicht erreichbar oder Schema nicht migriert. Railway: DATABASE_URL pruefen und alembic upgrade head ausfuehren.";
  }
  if (res.status === 500) {
    return "Serverfehler beim Backend. Railway-Logs pruefen und Alembic-Migrationen ausfuehren (alembic upgrade head).";
  }
  if (res.status === 400) {
    return "Anfrage vom Backend abgelehnt (HTTP 400). TRUSTED_HOSTS muss den Host aus BACKEND_URL enthalten.";
  }
  if (res.status === 404) {
    return "Auth-Endpoint nicht gefunden. BACKEND_URL nur als Origin setzen (ohne /api/v1) und Vercel neu deployen.";
  }
  if (res.status === 401) {
    return "Anmeldung fehlgeschlagen. E-Mail und Passwort pruefen.";
  }

  return `API-Anfrage fehlgeschlagen (HTTP ${res.status}).`;
}

function isBackendUnreachableResponse(res: Response, body: unknown): boolean {
  const code = readDetailCode(body);
  if (code === "BACKEND_UNREACHABLE" || code === "BACKEND_URL_MISSING") return true;
  return res.status === 502 || res.status === 504;
}

async function parse<T>(res: Response): Promise<T> {
  const body = await readResponseBody(res);
  if (!res.ok) {
    const code = readDetailCode(body);
    if (code === "BACKEND_URL_MISSING") {
      throw new Error(BACKEND_URL_MISSING_HINT);
    }
    if (isBackendUnreachableResponse(res, body)) {
      throw new Error(BACKEND_UNREACHABLE_HINT);
    }
    throw new Error(resolveAuthErrorMessage(res, body));
  }
  return body as T;
}

/** User-facing hint for register/login forms when backend/proxy errors occur. */
export function isAuthInfrastructureError(message: string): boolean {
  const lower = message.toLowerCase();
  return (
    lower.includes("backend") ||
    lower.includes("backend_url") ||
    lower.includes("datenbank") ||
    lower.includes("schema nicht migriert") ||
    lower.includes("alembic") ||
    lower.includes("jwt_secret") ||
    lower.includes("jwt-signatur") ||
    lower.includes("auth_jwt_not_configured") ||
    lower.includes("502") ||
    lower.includes("503") ||
    lower.includes("504")
  );
}

async function backendAuthFetch(path: string, init?: RequestInit): Promise<Response> {
  try {
    // Rewrite zuerst: auf allen Vercel-Deploys mit BACKEND_URL stabil (Route Handler optional).
    const rewrite = await fetch(`${AUTH_REWRITE_BASE}${path}`, init);
    if (rewrite.status !== 404) {
      return rewrite;
    }
    return await fetch(`${AUTH_BASE}${path}`, init);
  } catch {
    throw new Error(BACKEND_UNREACHABLE_HINT);
  }
}

export async function register(payload: { email: string; password: string; role?: string; full_name?: string }) {
  const res = await backendAuthFetch("/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return parse<AuthUser>(res);
}

export async function login(payload: { email: string; password: string }) {
  const res = await backendAuthFetch("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  const tokens = await parse<TokenResponse>(res);
  setAccessToken(tokens.access_token);
  return tokens;
}

export async function me() {
  const res = await backendAuthFetch("/me", {
    credentials: "include",
    cache: "no-store",
    headers: { ...bearerAuthHeaders() },
  });
  return parse<AuthUser>(res);
}

export async function requestPasswordReset(email: string) {
  const res = await backendAuthFetch("/forgot-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim() }),
  });
  return parse<{ status: string; message: string }>(res);
}

export async function resetPassword(payload: { token: string; password: string }) {
  const res = await backendAuthFetch("/reset-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parse<{ status: string; message: string }>(res);
}

export async function logout() {
  const csrf = getCsrfTokenFromCookie();
  const res = await backendAuthFetch("/logout", {
    method: "POST",
    credentials: "include",
    headers: { ...(csrf ? { "X-CSRF-Token": csrf } : {}), ...bearerAuthHeaders() },
  });
  const result = await parse<{ status: string }>(res);
  setAccessToken(null);
  return result;
}
