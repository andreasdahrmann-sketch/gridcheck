import { proxyToBackend } from "@/lib/server/backend-proxy";

export async function POST(request: Request) {
  return proxyToBackend("/api/v1/auth/logout", request, { forwardCookies: true });
}
