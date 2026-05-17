import { getCsrfTokenFromCookie } from "@/lib/api/csrf";
import { bearerAuthHeaders, extractApiErrorMessage, setAccessToken } from "@/lib/api/session";

export type AuthUser = {
  id: number;
  email: string;
  role: string;
  full_name?: string | null;
};

type TokenResponse = {
  access_token: string;
  refresh_token?: string;
  token_type: string;
};

/** Same-origin route handlers (app/api/auth/*) proxy server-side to FastAPI. */
const BASE = "/api/auth";

const BACKEND_UNREACHABLE_HINT =
  "Backend nicht erreichbar. Vercel: BACKEND_URL auf die Railway-HTTPS-URL setzen (nur Origin, ohne /api/v1). Railway: GET /health pruefen. Lokal: uvicorn auf Port 8000.";

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
  const parsed = extractApiErrorMessage(body, "");
  if (parsed) return parsed;

  if (res.status === 503) {
    return (
      extractApiErrorMessage(body, "") ||
      "Datenbank nicht erreichbar oder Schema nicht migriert (alembic upgrade head auf Railway)."
    );
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

  return `API-Anfrage fehlgeschlagen (HTTP ${res.status}).`;
}

async function parse<T>(res: Response): Promise<T> {
  const body = await readResponseBody(res);
  if (!res.ok) {
    if (res.status >= 502 && res.status <= 504) {
      throw new Error(BACKEND_UNREACHABLE_HINT);
    }
    throw new Error(resolveAuthErrorMessage(res, body));
  }
  return body as T;
}

async function backendAuthFetch(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${BASE}${path}`, init);
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
