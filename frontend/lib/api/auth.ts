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

const BASE = "/api/backend/api/v1/auth";

async function parse<T>(res: Response): Promise<T> {
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(extractApiErrorMessage(body, "API request failed"));
  }
  return body as T;
}

export async function register(payload: { email: string; password: string; role?: string; full_name?: string }) {
  const res = await fetch(`${BASE}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return parse<AuthUser>(res);
}

export async function login(payload: { email: string; password: string }) {
  const res = await fetch(`${BASE}/login`, {
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
  const res = await fetch(`${BASE}/me`, {
    credentials: "include",
    cache: "no-store",
    headers: { ...bearerAuthHeaders() },
  });
  return parse<AuthUser>(res);
}

export async function logout() {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(`${BASE}/logout`, {
    method: "POST",
    credentials: "include",
    headers: { ...(csrf ? { "X-CSRF-Token": csrf } : {}), ...bearerAuthHeaders() },
  });
  const result = await parse<{ status: string }>(res);
  setAccessToken(null);
  return result;
}
