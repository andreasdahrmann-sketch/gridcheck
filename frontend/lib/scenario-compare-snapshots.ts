import type { GridCheckResult, Szenario } from "@/types";

const STORAGE_PREFIX = "gridcheck:compare:";
const MAX_SNAPSHOTS = 2;

export type ScenarioCompareSnapshot = {
  id: string;
  savedAt: string;
  revisionHash?: string;
  label: string;
  score: number;
  konfidenz: number;
  machbarkeit_stufe: string;
  delta_u_pct: number;
  n1_level?: string;
  kosten_basis_eur?: number;
  szenarien: Szenario[];
  worst_case: Szenario;
};

function storageKey(projectId: string | number): string {
  return `${STORAGE_PREFIX}${projectId}`;
}

function readRaw(projectId: string | number): ScenarioCompareSnapshot[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.sessionStorage.getItem(storageKey(projectId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ScenarioCompareSnapshot[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeRaw(projectId: string | number, items: ScenarioCompareSnapshot[]): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(storageKey(projectId), JSON.stringify(items.slice(0, MAX_SNAPSHOTS)));
}

export function listCompareSnapshots(projectId: string | number): ScenarioCompareSnapshot[] {
  return readRaw(projectId);
}

export function snapshotFromResult(result: GridCheckResult, label?: string): ScenarioCompareSnapshot {
  const hash = result.revision?.hash;
  const ts = result.revision?.timestamp ?? new Date().toISOString();
  return {
    id: hash ?? `local-${Date.now()}`,
    savedAt: new Date().toISOString(),
    revisionHash: hash,
    label: label ?? `Analyse ${new Date(ts).toLocaleString("de-DE")}`,
    score: result.score ?? 0,
    konfidenz: result.konfidenz ?? 0,
    machbarkeit_stufe: result.machbarkeit_stufe ?? "—",
    delta_u_pct: result.delta_u_pct ?? result.worst_case?.delta_u_pct ?? 0,
    n1_level: result.n1?.n1_klasse,
    kosten_basis_eur: result.kosten_bandbreite?.basis_eur ?? result.kosten_indikation_eur,
    szenarien: result.szenarien ?? [],
    worst_case: result.worst_case ?? {
      name: "—",
      beschreibung: "",
      delta_u_pct: 0,
      delta_u_isRise: false,
      trafo_auslastung_pct: 0,
      leitung_auslastung_pct: 0,
      ik_kA: 0,
      bewertung: "ok",
    },
  };
}

/** Behaelt die zwei juengsten Snapshots (FIFO). */
export function pushCompareSnapshot(projectId: string | number, result: GridCheckResult): void {
  const next = snapshotFromResult(result);
  const existing = readRaw(projectId).filter((s) => s.id !== next.id);
  writeRaw(projectId, [next, ...existing].slice(0, MAX_SNAPSHOTS));
}

export function clearCompareSnapshots(projectId: string | number): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(storageKey(projectId));
}
