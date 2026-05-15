// Zentrale API-Typen (keine "any" laut .cursorrules)
export type ApiError = {
  message: string;
  status?: number;
  cause?: unknown;
};

export type HealthResponse = {
  status: "ok" | "degraded" | "down";
  version: string;
};
