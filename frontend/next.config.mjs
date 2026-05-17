/**
 * Rewrites are resolved at build time — BACKEND_URL must be set when `next build` runs on Vercel.
 * Route Handlers (/api/auth/*, /api/health) read BACKEND_URL again at runtime (serverless).
 * Set BACKEND_URL for Production and Preview in Vercel (not build-only).
 */
/** @type {import("next").NextConfig} */
const rawBackendUrl = process.env.BACKEND_URL?.trim().replace(/[\r\n]+/g, "");

if (process.env.VERCEL === "1" && !rawBackendUrl) {
  throw new Error(
    "BACKEND_URL ist fuer Vercel-Deploys erforderlich (Build und Runtime). Nur Origin, z. B. https://gridcheck-production.up.railway.app",
  );
}

if (rawBackendUrl && !/^https?:\/\//.test(rawBackendUrl)) {
  throw new Error("BACKEND_URL muss eine absolute http(s)-URL sein. Aktueller Wert: [" + rawBackendUrl + "]");
}

const isLocalBackendUrl =
  rawBackendUrl && /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?\/?$/i.test(rawBackendUrl);

const backendOrigin = (rawBackendUrl || "http://localhost:8000").replace(/\/+$/, "");

if (rawBackendUrl && !isLocalBackendUrl && backendOrigin.startsWith("http://")) {
  throw new Error(
    "BACKEND_URL muss https:// verwenden (ausser localhost). http:// kann POST-Rewrites per Redirect brechen.",
  );
}

if (rawBackendUrl && /\/api(\/v\d+)?\/?$/i.test(rawBackendUrl)) {
  throw new Error(
    "BACKEND_URL darf kein /api- oder /api/v1-Suffix enthalten (nur Origin, z. B. https://your-app.up.railway.app).",
  );
}

/** @type {import("next").NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    if (!rawBackendUrl || isLocalBackendUrl) return [];
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backendOrigin}/:path*`,
      },
    ];
  },
};

export default nextConfig;
