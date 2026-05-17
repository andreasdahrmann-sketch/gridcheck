import { proxyToBackend } from "@/lib/server/backend-proxy";

export async function GET(request: Request) {
  return proxyToBackend("/api/v1/auth/me", request, { forwardCookies: true });
}
