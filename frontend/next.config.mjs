/**
 * Rewrites are resolved at build time — BACKEND_URL should be set when `next build` runs on Vercel.
 * Route Handlers (/api/auth/*, /api/health) read BACKEND_URL again at runtime (serverless).
 * Set BACKEND_URL for Production and Preview in Vercel (not build-only).
 */
/** Project-specific production default when Vercel omits BACKEND_URL (GridCheck prod Railway only). */
const VERCEL_PROD_BACKEND_FALLBACK = "https://gridcheck-production.up.railway.app";

/** @type {import("next").NextConfig} */
let rawBackendUrl = process.env.BACKEND_URL?.trim().replace(/[\r\n]+/g, "") ?? "";

if (process.env.VERCEL === "1" && !rawBackendUrl) {
  console.warn(
    "[next.config] BACKEND_URL fehlt auf Vercel — verwende Projekt-Fallback:",
    VERCEL_PROD_BACKEND_FALLBACK,
    "(bitte BACKEND_URL in Vercel Project Settings setzen und redeployen)",
  );
  rawBackendUrl = VERCEL_PROD_BACKEND_FALLBACK;
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
  // perf: lucide-react exportiert >1.000 Icons; ohne Per-Icon-Tree-Shaking
  // landet ein grosser Teil im initial bundle. optimizePackageImports
  // erzwingt Per-Icon-Auflösung (Next 14.2+).
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
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
