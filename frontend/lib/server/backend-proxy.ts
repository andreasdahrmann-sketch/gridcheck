/** Server-side proxy to FastAPI (used by /api/auth/* route handlers). */

import { getBackendOrigin } from "@/lib/server/backend-config";

export { getBackendOrigin };

function buildBackendUrl(backendPath: string): string {
  const path = backendPath.startsWith("/") ? backendPath : `/${backendPath}`;
  return `${getBackendOrigin()}${path}`;
}

function forwardResponseHeaders(upstream: Response): Headers {
  const headers = new Headers();
  const contentType = upstream.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);

  if (typeof upstream.headers.getSetCookie === "function") {
    for (const cookie of upstream.headers.getSetCookie()) {
      headers.append("Set-Cookie", cookie);
    }
  } else {
    const setCookie = upstream.headers.get("set-cookie");
    if (setCookie) headers.set("Set-Cookie", setCookie);
  }

  return headers;
}

export async function proxyToBackend(
  backendPath: string,
  request: Request,
  options?: { forwardCookies?: boolean; forwardAuth?: boolean },
): Promise<Response> {
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  headers.set("Accept", request.headers.get("accept") ?? "application/json");

  if (options?.forwardCookies) {
    const cookie = request.headers.get("cookie");
    if (cookie) headers.set("Cookie", cookie);
  }
  if (options?.forwardAuth !== false) {
    const authorization = request.headers.get("authorization");
    if (authorization) headers.set("Authorization", authorization);
    const csrf = request.headers.get("x-csrf-token");
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
    redirect: "manual",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  let backendUrl: string;
  try {
    backendUrl = buildBackendUrl(backendPath);
  } catch {
    return Response.json(
      {
        detail: {
          code: "BACKEND_URL_MISSING",
          message: "BACKEND_URL fehlt zur Laufzeit auf Vercel",
          hint: "Vercel Project Settings: BACKEND_URL fuer Production und Preview setzen, dann Redeploy.",
        },
      },
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, init);
  } catch {
    const missingRuntimeUrl =
      process.env.VERCEL === "1" && !(process.env.BACKEND_URL?.trim());
    return Response.json(
      {
        detail: {
          code: missingRuntimeUrl ? "BACKEND_URL_MISSING" : "BACKEND_UNREACHABLE",
          message: missingRuntimeUrl
            ? "BACKEND_URL fehlt zur Laufzeit auf Vercel"
            : "Backend nicht erreichbar",
          hint: missingRuntimeUrl
            ? "Vercel Project Settings: BACKEND_URL fuer Production und Preview setzen, dann Redeploy."
            : "Vercel BACKEND_URL und Railway GET /health pruefen. Lokal: uvicorn auf Port 8000.",
        },
      },
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }

  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: forwardResponseHeaders(upstream),
  });
}
