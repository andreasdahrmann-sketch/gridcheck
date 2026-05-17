"use client";

import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api/health";
import { extractApiErrorMessage } from "@/lib/api/session";
import type { HealthResponse, ApiError } from "@/types/api";

type ProbeResult = {
  status: number;
  ok: boolean;
  ms: number;
  message: string;
  bodyPreview?: string;
};

type ConfigProbe = {
  ok: boolean;
  configured: boolean;
  host: string | null;
  upstreamStatus?: number;
  backend?: unknown;
  error?: { code?: string; message?: string; hint?: string };
};

type State =
  | { kind: "loading" }
  | {
      kind: "ok";
      health: HealthResponse;
      healthMs: number;
      registerProbe: ProbeResult;
      configProbe: ConfigProbe;
    }
  | { kind: "error"; error: ApiError; registerProbe?: ProbeResult | null; configProbe?: ConfigProbe | null };

async function probeConfigEndpoint(): Promise<ConfigProbe> {
  const res = await fetch("/api/health", { cache: "no-store" });
  const data = (await res.json().catch(() => ({}))) as {
    ok?: boolean;
    config?: { configured?: boolean; host?: string | null };
    backend?: unknown;
    upstreamStatus?: number;
    error?: { code?: string; message?: string; hint?: string };
  };
  return {
    ok: Boolean(data.ok),
    configured: Boolean(data.config?.configured),
    host: data.config?.host ?? null,
    upstreamStatus: data.upstreamStatus,
    backend: data.backend,
    error: data.error,
  };
}

async function probeRegisterEndpoint(): Promise<ProbeResult> {
  const t0 = performance.now();
  const res = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    credentials: "include",
    body: JSON.stringify({
      email: `probe-${Date.now()}@example.com`,
      password: "short",
      role: "projektierer",
    }),
  });
  const text = await res.text().catch(() => "");
  let body: unknown = {};
  if (text) {
    try {
      body = JSON.parse(text) as unknown;
    } catch {
      body = { detail: { message: "Kein JSON", hint: text.slice(0, 160) } };
    }
  }

  const expectedClientError = res.status === 400 || res.status === 422;
  const message = expectedClientError
    ? `Register-Route erreichbar (${extractApiErrorMessage(body, "Passwort-Validierung")})`
    : extractApiErrorMessage(body, `Unerwarteter Status HTTP ${res.status}`);

  return {
    status: res.status,
    ok: expectedClientError,
    ms: Math.round(performance.now() - t0),
    message,
    bodyPreview: text.slice(0, 400),
  };
}

function RegisterProbeCard({ probe }: { probe: ProbeResult }) {
  return (
    <section
      style={{
        marginTop: 16,
        padding: 16,
        background: probe.ok ? "#e8f7ee" : "#fdecea",
        border: `1px solid ${probe.ok ? "#2e7d32" : "#c62828"}`,
        borderRadius: 8,
      }}
    >
      <p style={{ fontWeight: 600, color: probe.ok ? "#2e7d32" : "#c62828", margin: 0 }}>
        {probe.ok ? "✅" : "❌"} Register-Probe HTTP {probe.status} ({probe.ms} ms)
      </p>
      <p style={{ marginTop: 8 }}>{probe.message}</p>
      {probe.bodyPreview ? (
        <pre style={{ marginTop: 12, background: "#fff", padding: 12, borderRadius: 6, fontSize: 12 }}>
          {probe.bodyPreview}
        </pre>
      ) : null}
    </section>
  );
}

export default function ApiTestPage() {
  const [state, setState] = useState<State>({ kind: "loading" });

  async function run() {
    setState({ kind: "loading" });
    const t0 = performance.now();
    let registerProbe: ProbeResult | null = null;
    let configProbe: ConfigProbe | null = null;
    try {
      configProbe = await probeConfigEndpoint();
      const data = await getHealth();
      registerProbe = await probeRegisterEndpoint();
      setState({
        kind: "ok",
        health: data,
        healthMs: Math.round(performance.now() - t0),
        registerProbe,
        configProbe,
      });
    } catch (e) {
      try {
        configProbe = configProbe ?? (await probeConfigEndpoint());
        registerProbe = await probeRegisterEndpoint();
      } catch {
        registerProbe = null;
      }
      setState({ kind: "error", error: e as ApiError, registerProbe, configProbe });
    }
  }

  useEffect(() => {
    run();
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: 32, maxWidth: 720 }}>
      <h1 style={{ fontSize: 24, marginBottom: 8 }}>GridCheck — Backend-Verbindungstest</h1>
      <p style={{ color: "#666", marginBottom: 24 }}>
        Config: <code>/api/health</code> (Runtime BACKEND_URL + Railway). Rewrite: <code>/api/backend/health</code>.
        Register: <code>/api/auth/register</code>.
      </p>
      {(state.kind === "ok" || state.configProbe) && (
        <section
          style={{
            marginBottom: 16,
            padding: 16,
            background: state.kind === "ok" && state.configProbe.ok ? "#e8f4fd" : "#fff8e6",
            border: "1px solid #90caf9",
            borderRadius: 8,
          }}
        >
          <p style={{ fontWeight: 600, margin: 0 }}>
            {state.kind === "ok" ? (state.configProbe.ok ? "✅" : "⚠️") : "ℹ️"} Runtime BACKEND_URL
          </p>
          <pre style={{ marginTop: 12, background: "#fff", padding: 12, borderRadius: 6, fontSize: 12 }}>
            {JSON.stringify(state.kind === "ok" ? state.configProbe : state.configProbe, null, 2)}
          </pre>
        </section>
      )}
      {state.kind === "loading" && <p>⏳ Pruefe Backend...</p>}
      {state.kind === "ok" && (
        <>
          <section style={{ padding: 16, background: "#e8f7ee", border: "1px solid #2e7d32", borderRadius: 8 }}>
            <p style={{ fontWeight: 600, color: "#2e7d32", margin: 0 }}>✅ Health OK ({state.healthMs} ms)</p>
            <pre style={{ marginTop: 12, background: "#fff", padding: 12, borderRadius: 6 }}>
              {JSON.stringify(state.health, null, 2)}
            </pre>
          </section>
          <RegisterProbeCard probe={state.registerProbe} />
        </>
      )}
      {state.kind === "error" && (
        <>
          <section style={{ padding: 16, background: "#fdecea", border: "1px solid #c62828", borderRadius: 8 }}>
            <p style={{ fontWeight: 600, color: "#c62828", margin: 0 }}>❌ Health fehlgeschlagen</p>
            <pre style={{ marginTop: 12, background: "#fff", padding: 12, borderRadius: 6 }}>
              {JSON.stringify(state.error, null, 2)}
            </pre>
          </section>
          {state.registerProbe ? <RegisterProbeCard probe={state.registerProbe} /> : null}
        </>
      )}
      <button type="button" onClick={run} style={{ marginTop: 16, padding: "8px 16px", cursor: "pointer" }}>
        🔄 Erneut pruefen
      </button>
    </main>
  );
}
