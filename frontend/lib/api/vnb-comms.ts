import { getCsrfTokenFromCookie } from "@/lib/api/csrf";
import { bearerAuthHeaders } from "@/lib/api/session";

export type VnbCommsCategory = "kapazitaetshinweis" | "redispatch" | "infrastruktur" | "sonstiges";

export type VnbThreadSummary = {
  id: number;
  board_scope: string;
  title: string;
  category: VnbCommsCategory;
  target_vnb_region?: string | null;
  created_by_user_id: number;
  created_at: string;
  last_message_at?: string | null;
  message_count: number;
  last_message_preview?: string | null;
};

export type VnbMessageItem = {
  id: number;
  thread_id: number;
  sender_user_id: number;
  body: string;
  created_at: string;
};

export type VnbThreadDetail = VnbThreadSummary & {
  messages: VnbMessageItem[];
};

const BASE = "/api/backend/api/v1/vnb/comms";

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body?.detail;
    const message =
      (typeof detail === "object" && detail && "message" in detail && String(detail.message)) ||
      "API-Anfrage fehlgeschlagen";
    const err = new Error(message) as Error & { code?: string };
    if (typeof detail === "object" && detail && "code" in detail) {
      err.code = String(detail.code);
    }
    throw err;
  }
  return res.json() as Promise<T>;
}

export async function listVnbThreads(limit = 100) {
  const params = new URLSearchParams({ limit: String(limit) });
  const res = await fetch(`${BASE}/threads?${params}`, {
    credentials: "include",
    cache: "no-store",
    headers: { ...bearerAuthHeaders() },
  });
  return parse<VnbThreadSummary[]>(res);
}

export async function getVnbThread(threadId: number) {
  const res = await fetch(`${BASE}/threads/${threadId}`, {
    credentials: "include",
    cache: "no-store",
    headers: { ...bearerAuthHeaders() },
  });
  return parse<VnbThreadDetail>(res);
}

export async function createVnbThread(payload: {
  title: string;
  category: VnbCommsCategory;
  body: string;
  target_vnb_region?: string;
}) {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(`${BASE}/threads`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...bearerAuthHeaders(),
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    body: JSON.stringify(payload),
  });
  return parse<VnbThreadDetail>(res);
}

export async function postVnbThreadMessage(threadId: number, body: string) {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(`${BASE}/threads/${threadId}/messages`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...bearerAuthHeaders(),
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    body: JSON.stringify({ body }),
  });
  return parse<VnbThreadDetail>(res);
}

export const VNB_COMMS_CATEGORY_LABELS: Record<VnbCommsCategory, string> = {
  kapazitaetshinweis: "Kapazitaetshinweis",
  redispatch: "Redispatch",
  infrastruktur: "Infrastruktur",
  sonstiges: "Sonstiges",
};
