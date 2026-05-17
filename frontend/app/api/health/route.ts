import { getBackendConfigStatus } from "@/lib/server/backend-config";
import { proxyToBackend } from "@/lib/server/backend-proxy";

export const dynamic = "force-dynamic";

export async function GET() {
  const config = getBackendConfigStatus();

  if (!config.configured) {
    return Response.json(
      {
        ok: false,
        frontend: "gridcheck",
        backend: null,
        config,
        error: {
          code: "BACKEND_URL_MISSING",
          message: "BACKEND_URL ist nicht gesetzt",
          hint:
            "Vercel: BACKEND_URL auf die Railway-HTTPS-URL setzen (nur Origin). Lokal: .env.local mit BACKEND_URL=http://localhost:8000",
        },
      },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }

  const upstream = await proxyToBackend("/health", new Request("http://localhost/api/health"));
  const text = await upstream.text();
  let backend: unknown = null;
  try {
    backend = text ? (JSON.parse(text) as unknown) : null;
  } catch {
    backend = { raw: text.slice(0, 400) };
  }

  return Response.json(
    {
      ok: upstream.ok,
      frontend: "gridcheck",
      backend,
      config,
      upstreamStatus: upstream.status,
    },
    {
      status: upstream.ok ? 200 : upstream.status >= 400 ? upstream.status : 502,
      headers: { "Cache-Control": "no-store" },
    },
  );
}
