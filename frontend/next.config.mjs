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

/**
 * Security-Header — siehe `.cursor/rules/02-frontend.mdc` und `04-deployment.mdc`.
 *
 * CSP ist bewusst konservativ. Externe Hosts:
 *  - Mapbox (Karten / Geocoding):       https://api.mapbox.com, https://*.mapbox.com,
 *                                       https://events.mapbox.com
 *  - OpenStreetMap-Tiles (Leaflet):     https://*.tile.openstreetmap.org,
 *                                       https://tile.openstreetmap.org
 *  - Nominatim (PLZ-/Adresssuche):      https://nominatim.openstreetmap.org
 *  - Sentry (optional, falls aktiviert):https://*.sentry.io
 *  - Google Fonts (Inter @import in
 *    globals.css):                      https://fonts.googleapis.com (style),
 *                                       https://fonts.gstatic.com (font-src)
 *
 * BACKEND_URL wird, falls gesetzt, additiv in `connect-src` aufgenommen
 * (für Browser-Calls zu /api/backend/*; im Vercel-Setup laufen diese Calls
 *  same-origin via rewrites, in lokalen Setups ggf. cross-origin).
 *
 * Stripe ist aktuell nicht aktiv. Wenn Stripe später integriert wird,
 *   - script-src:  https://js.stripe.com
 *   - frame-src:   https://js.stripe.com, https://hooks.stripe.com
 *   - connect-src: https://api.stripe.com
 * ergänzen.
 *
 * 'unsafe-inline' für script-src ist für Next.js-Hydration/Inline-Scripts
 * notwendig. 'unsafe-eval' nur in Development (next dev) zugelassen.
 */
const isDev = process.env.NODE_ENV !== "production";

const cspBackendOrigin = rawBackendUrl ? backendOrigin : "";

const cspDirectives = {
  "default-src": ["'self'"],
  "script-src": [
    "'self'",
    "'unsafe-inline'",
    ...(isDev ? ["'unsafe-eval'"] : []),
  ],
  "style-src": [
    "'self'",
    "'unsafe-inline'",
    "https://fonts.googleapis.com",
  ],
  "font-src": ["'self'", "data:", "https://fonts.gstatic.com"],
  "img-src": [
    "'self'",
    "data:",
    "blob:",
    "https://*.tile.openstreetmap.org",
    "https://tile.openstreetmap.org",
    "https://api.mapbox.com",
    "https://*.mapbox.com",
  ],
  "connect-src": [
    "'self'",
    "https://nominatim.openstreetmap.org",
    "https://api.mapbox.com",
    "https://*.mapbox.com",
    "https://events.mapbox.com",
    "https://*.sentry.io",
    ...(cspBackendOrigin ? [cspBackendOrigin] : []),
    ...(isDev ? ["ws://localhost:*", "http://localhost:*"] : []),
  ],
  "worker-src": ["'self'", "blob:"],
  "frame-ancestors": ["'none'"],
  "frame-src": ["'self'"],
  "base-uri": ["'self'"],
  "form-action": ["'self'"],
  "object-src": ["'none'"],
};

const cspString = Object.entries(cspDirectives)
  .map(([directive, values]) => `${directive} ${values.join(" ")}`)
  .concat(["upgrade-insecure-requests"])
  .join("; ");

const securityHeaders = [
  // HSTS: zwei Jahre + Preload. Wirkt nur über https; auf http (lokal) ignoriert der Browser den Header.
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(self), interest-cohort=()",
  },
  { key: "Content-Security-Policy", value: cspString },
];

/** @type {import("next").NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // perf: lucide-react exportiert >1.000 Icons; ohne Per-Icon-Tree-Shaking
  // landet ein grosser Teil im initial bundle. optimizePackageImports
  // erzwingt Per-Icon-Auflösung (Next 14.2+).
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
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
