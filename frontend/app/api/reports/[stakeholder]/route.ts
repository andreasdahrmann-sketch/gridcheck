import { getBackendOrigin } from "@/lib/server/backend-config";

const ALLOWED_STAKEHOLDERS = new Set(["projektierer", "vnb", "invest"]);

function forwardPdfResponseHeaders(upstream: Response): Headers {
  const headers = new Headers();
  const contentType = upstream.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  const disposition = upstream.headers.get("content-disposition");
  if (disposition) headers.set("Content-Disposition", disposition);
  for (const name of [
    "x-gridcheck-report-revision-hash",
    "x-gridcheck-report-revision-uuid",
    "x-gridcheck-report-verify-path",
    "x-gridcheck-source-revision-hash",
    "x-gridcheck-source-verify-path",
  ]) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  return headers;
}

export async function POST(
  request: Request,
  context: { params: { stakeholder: string } },
): Promise<Response> {
  const stakeholder = context.params.stakeholder?.trim().toLowerCase();
  if (!stakeholder || !ALLOWED_STAKEHOLDERS.has(stakeholder)) {
    return Response.json(
      {
        detail: {
          code: "REPORT_STAKEHOLDER_INVALID",
          message: "Unbekannter Report-Typ.",
          hint: "Erlaubt sind projektierer, vnb oder invest.",
        },
      },
      { status: 400 },
    );
  }

  const format = new URL(request.url).searchParams.get("format") ?? "pdf";
  const backendUrl = `${getBackendOrigin()}/api/v2/reports/${stakeholder}?format=${encodeURIComponent(format)}`;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  headers.set("Accept", request.headers.get("accept") ?? "application/pdf");

  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);

  const authorization = request.headers.get("authorization");
  if (authorization) headers.set("Authorization", authorization);

  const csrf = request.headers.get("x-csrf-token");
  if (csrf) headers.set("X-CSRF-Token", csrf);

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl, {
      method: "POST",
      headers,
      body: await request.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    return Response.json(
      {
        detail: {
          code: "BACKEND_UNREACHABLE",
          message: "Backend nicht erreichbar",
          hint: "Bitte BACKEND_URL auf Vercel pruefen und Railway /health testen.",
        },
      },
      { status: 502 },
    );
  }

  const responseHeaders = forwardPdfResponseHeaders(upstream);
  const payload = await upstream.arrayBuffer();

  if (!upstream.ok) {
    if (upstream.headers.get("content-type")?.includes("application/json")) {
      return new Response(payload, { status: upstream.status, headers: responseHeaders });
    }
    return new Response(payload, { status: upstream.status, headers: responseHeaders });
  }

  return new Response(payload, { status: upstream.status, headers: responseHeaders });
}
