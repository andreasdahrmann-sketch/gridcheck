import type { ApiError } from "@/types/api";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api/backend";
const DEFAULT_TIMEOUT_MS = 8000;

export async function apiGet<T>(path: string, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${BASE}${path}`, {
      method: "GET",
      headers: { "Accept": "application/json" },
      signal: controller.signal,
      cache: "no-store",
    });
    if (!res.ok) {
      const err: ApiError = { message: `HTTP ${res.status}`, status: res.status };
      throw err;
    }
    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      const err: ApiError = { message: `Timeout nach ${timeoutMs}ms` };
      throw err;
    }
    if (typeof e === "object" && e !== null && "message" in e) throw e as ApiError;
    const err: ApiError = { message: "Unbekannter Netzwerkfehler", cause: e };
    throw err;
  } finally {
    clearTimeout(timer);
  }
}
