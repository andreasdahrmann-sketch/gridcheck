"use client";
import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api/health";
import type { HealthResponse, ApiError } from "@/types/api";

type State =
  | { kind: "loading" }
  | { kind: "ok"; data: HealthResponse; ms: number }
  | { kind: "error"; error: ApiError };

export default function ApiTestPage() {
  const [state, setState] = useState<State>({ kind: "loading" });

  async function run() {
    setState({ kind: "loading" });
    const t0 = performance.now();
    try {
      const data = await getHealth();
      setState({ kind: "ok", data, ms: Math.round(performance.now() - t0) });
    } catch (e) {
      setState({ kind: "error", error: e as ApiError });
    }
  }

  useEffect(() => { run(); }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: 32, maxWidth: 720 }}>
      <h1 style={{ fontSize: 24, marginBottom: 8 }}>GridCheck — Backend-Verbindungstest</h1>
      <p style={{ color: "#666", marginBottom: 24 }}>
        Frontend → <code>/api/backend/health</code> → Rewrite → FastAPI <code>:8000/health</code>
      </p>
      {state.kind === "loading" && <div>⏳ Pruefe Backend...</div>}
      {state.kind === "ok" && (
        <div style={{ padding: 16, background: "#e8f7ee", border: "1px solid #2e7d32", borderRadius: 8 }}>
          <div style={{ fontWeight: 600, color: "#2e7d32" }}>✅ Backend erreichbar ({state.ms} ms)</div>
          <pre style={{ marginTop: 12, background: "#fff", padding: 12, borderRadius: 6 }}>
{JSON.stringify(state.data, null, 2)}
          </pre>
        </div>
      )}
      {state.kind === "error" && (
        <div style={{ padding: 16, background: "#fdecea", border: "1px solid #c62828", borderRadius: 8 }}>
          <div style={{ fontWeight: 600, color: "#c62828" }}>❌ Fehler</div>
          <pre style={{ marginTop: 12, background: "#fff", padding: 12, borderRadius: 6 }}>
{JSON.stringify(state.error, null, 2)}
          </pre>
        </div>
      )}
      <button onClick={run} style={{ marginTop: 16, padding: "8px 16px", cursor: "pointer" }}>
        🔄 Erneut pruefen
      </button>
    </main>
  );
}
