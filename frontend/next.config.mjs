/**
 * Rewrites are resolved at build time — BACKEND_URL should be set when `next build` runs on Vercel.
 * Route Handlers (/api/auth/*, /api/health) read BACKEND_URL again at runtime (serverless).
 * Set BACKEND_URL for Production and Preview in Vercel (not build-only).
 */
/** @type {import("next").NextConfig} */
let rawBackendUrl = process.env.BACKEND_URL?.trim().replace(/[\r\n]+/g, "") ?? "";

if (process.env.VERCEL === "1" && !rawBackendUrl) {
  throw new Error(
    "BACKEND_URL fehlt auf Vercel. Bitte BACKEND_URL fuer Production und Preview in den Vercel Project Settings setzen.",
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

/**
 * perf: Bundle-Analyzer (BL-PERF-006) nur aktiv bei ANALYZE=true.
 *
 * Wrapper ist optional — wenn `@next/bundle-analyzer` nicht installiert
 * ist (z. B. frischer Clone vor `npm install`), bleibt die Config
 * unverändert. Top-level await ist in ESM (.mjs) ab Node 14.8 erlaubt
 * und wird von Next 14.2 + Node 20 unterstützt (siehe .nvmrc / engines).
 *
 * Output: frontend/.next/analyze/{client,nodejs,edge}.html
 * Doku: docs/PERF_BASELINE.md
 */
let withBundleAnalyzer = (cfg) => cfg;
if (process.env.ANALYZE === "true") {
  try {
    const ba = (await import("@next/bundle-analyzer")).default;
    withBundleAnalyzer = ba({ enabled: true });
  } catch (err) {
    console.warn(
      "[next.config] ANALYZE=true gesetzt, aber @next/bundle-analyzer nicht installiert. " +
        "Bitte `npm install` ausführen (siehe docs/PERF_BASELINE.md). Build läuft ohne Analyzer.",
      err?.message ?? err,
    );
  }
}

export default withBundleAnalyzer(nextConfig);
