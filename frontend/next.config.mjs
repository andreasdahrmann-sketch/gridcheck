/** @type {import('next').NextConfig} */
/** Build-only fallback when Vercel has no BACKEND_URL yet (rewrites need a valid https origin). */
const VERCEL_BUILD_PLACEHOLDER_BACKEND = "https://placeholder.railway.app";

let rawBackendUrl = process.env.BACKEND_URL?.trim();

if (process.env.VERCEL === "1" && !rawBackendUrl) {
  console.warn(
    "[next.config] BACKEND_URL fehlt auf Vercel — Platzhalter",
    VERCEL_BUILD_PLACEHOLDER_BACKEND,
    "(Auth/API funktionieren erst nach Setzen der Railway-HTTPS-Origin ohne /api/v1).",
  );
  rawBackendUrl = VERCEL_BUILD_PLACEHOLDER_BACKEND;
}

if (rawBackendUrl && !/^https?:\/\//.test(rawBackendUrl)) {
  throw new Error("BACKEND_URL muss eine absolute http(s)-URL sein.");
}

const isLocalBackendUrl =
  rawBackendUrl && /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?\/?$/i.test(rawBackendUrl);

if (rawBackendUrl && !isLocalBackendUrl && rawBackendUrl.startsWith("http://")) {
  throw new Error(
    "BACKEND_URL muss https:// verwenden (ausser localhost). http:// kann POST-Rewrites per Redirect brechen.",
  );
}

if (process.env.VERCEL === "1" && rawBackendUrl && !rawBackendUrl.startsWith("https://")) {
  throw new Error("BACKEND_URL auf Vercel muss mit https:// beginnen.");
}

if (rawBackendUrl && /\/api(\/v\d+)?\/?$/i.test(rawBackendUrl)) {
  throw new Error(
    "BACKEND_URL darf kein /api- oder /api/v1-Suffix enthalten (nur Origin, z. B. https://your-app.up.railway.app).",
  );
}

const BACKEND_URL = (rawBackendUrl || "http://localhost:8000").replace(/\/+$/, "");

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      { source: '/api/backend/:path*', destination: `${BACKEND_URL}/:path*` },
    ];
  },
};

export default nextConfig;
