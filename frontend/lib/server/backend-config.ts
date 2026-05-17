/** Server-only BACKEND_URL helpers (Route Handlers, diagnostics). */

export function getConfiguredBackendUrl(): string | null {
  const raw = process.env.BACKEND_URL?.trim().replace(/[\r\n]+/g, "");
  if (!raw) return null;
  if (!/^https?:\/\//.test(raw)) return null;
  return raw.replace(/\/+$/, "");
}

export function isLocalBackendOrigin(origin: string): boolean {
  return /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(origin);
}

export function getBackendOrigin(): string {
  const configured = getConfiguredBackendUrl();
  if (configured) return configured;

  if (process.env.VERCEL === "1") {
    throw new Error(
      "BACKEND_URL fehlt zur Laufzeit auf Vercel. In Project Settings fuer Production und Preview setzen (nur Origin, z. B. https://….up.railway.app), dann Redeploy.",
    );
  }

  return "http://localhost:8000";
}

export function getBackendConfigStatus(): {
  configured: boolean;
  origin: string | null;
  host: string | null;
  isLocal: boolean;
  vercel: boolean;
} {
  const configured = getConfiguredBackendUrl();
  if (!configured) {
    return {
      configured: false,
      origin: null,
      host: null,
      isLocal: false,
      vercel: process.env.VERCEL === "1",
    };
  }
  let host: string | null = null;
  try {
    host = new URL(configured).host;
  } catch {
    host = null;
  }
  return {
    configured: true,
    origin: configured,
    host,
    isLocal: isLocalBackendOrigin(configured),
    vercel: process.env.VERCEL === "1",
  };
}
