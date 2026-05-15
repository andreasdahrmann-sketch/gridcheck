/** @type {import('next').NextConfig} */
const rawBackendUrl = process.env.BACKEND_URL?.trim();

if (process.env.VERCEL === "1" && !rawBackendUrl) {
  throw new Error("BACKEND_URL ist fuer Vercel-Deploys erforderlich.");
}

if (rawBackendUrl && !/^https?:\/\//.test(rawBackendUrl)) {
  throw new Error("BACKEND_URL muss eine absolute http(s)-URL sein.");
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
