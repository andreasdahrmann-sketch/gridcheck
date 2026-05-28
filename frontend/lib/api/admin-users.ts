import { getCsrfTokenFromCookie } from "@/lib/api/csrf";
import { bearerAuthHeaders } from "@/lib/api/session";

export type AdminVnbUser = {
  id: number;
  email: string;
  role: string;
  full_name: string | null;
  vnb_verification_status: string;
  netzbetreiber_verified: boolean;
};

const BASE = "/api/backend/api/v1/admin/users";

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : typeof detail?.message === "string"
          ? detail.message
          : "Admin-API-Anfrage fehlgeschlagen";
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export async function listPendingNetzbetreiber(): Promise<AdminVnbUser[]> {
  const res = await fetch(`${BASE}/pending-netzbetreiber`, {
    credentials: "include",
    cache: "no-store",
    headers: { ...bearerAuthHeaders() },
  });
  return parse<AdminVnbUser[]>(res);
}

export async function approveNetzbetreiber(userId: number): Promise<AdminVnbUser> {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(`${BASE}/${userId}/approve-netzbetreiber`, {
    method: "POST",
    credentials: "include",
    headers: {
      ...bearerAuthHeaders(),
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
  });
  return parse<AdminVnbUser>(res);
}
