import { getCsrfTokenFromCookie } from "@/lib/api/csrf";

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
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail?.message ?? "API request failed");
  }
  return res.json() as Promise<T>;
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
  return parse<TokenResponse>(res);
}

export async function me() {
  const res = await fetch(`${BASE}/me`, {
    credentials: "include",
    cache: "no-store",
  });
  return parse<AuthUser>(res);
}

export async function logout() {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(`${BASE}/logout`, {
    method: "POST",
    credentials: "include",
    headers: { ...(csrf ? { "X-CSRF-Token": csrf } : {}) },
  });
  return parse<{ status: string }>(res);
}
