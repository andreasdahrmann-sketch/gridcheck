"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  clearCompareSnapshots,
  getScenarioSlots,
  listCompareSnapshots,
  snapshotFromResult,
  type ScenarioCompareSnapshot,
} from "@/lib/scenario-compare-snapshots";
import type { GridCheckResult, Szenario } from "@/types";

type Props = {
  projectId: string;
  currentResult?: GridCheckResult | null;
};

function statusClass(bewertung: Szenario["bewertung"]): string {
  if (bewertung === "ok") return "bg-green-900/40 text-green-300";
  if (bewertung === "grenzwertig") return "bg-yellow-900/40 text-yellow-300";
  return "bg-red-900/40 text-red-300";
}

function CompareColumn({ title, snap }: { title: string; snap: ScenarioCompareSnapshot | null }) {
  if (!snap) {
    return (
      <div className="rounded-2xl border border-dashed border-white/15 bg-white/5 p-6 text-sm text-text-muted">
        <p className="font-semibold text-white">{title}</p>
        <p className="mt-2">Kein Snapshot — bitte eine Analyse im Projekt ausfuehren.</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-gray-900/60 p-6">
      <p className="text-xs uppercase tracking-wider text-text-dim">{title}</p>
      <p className="mt-1 text-lg font-semibold text-white">{snap.label}</p>
      {snap.revisionHash ? (
        <p className="mt-1 truncate font-mono text-xs text-text-muted" title={snap.revisionHash}>
          {snap.revisionHash.slice(0, 16)}…
        </p>
      ) : null}
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-text-dim">Score</dt>
          <dd className="font-semibold text-white">{snap.score}</dd>
        </div>
        <div>
          <dt className="text-text-dim">Konfidenz</dt>
          <dd className="font-semibold text-white">{snap.konfidenz} %</dd>
        </div>
        <div>
          <dt className="text-text-dim">Machbarkeit</dt>
          <dd className="text-white">{snap.machbarkeit_stufe}</dd>
        </div>
        <div>
          <dt className="text-text-dim">Delta u (Worst)</dt>
          <dd className="text-white">{snap.worst_case.delta_u_pct} %</dd>
        </div>
        <div>
          <dt className="text-text-dim">Trafo / Leitung</dt>
          <dd className="text-white">
            {snap.worst_case.trafo_auslastung_pct} % / {snap.worst_case.leitung_auslastung_pct} %
          </dd>
        </div>
        <div>
          <dt className="text-text-dim">Ik (Worst)</dt>
          <dd className="text-white">{snap.worst_case.ik_kA} kA</dd>
        </div>
      </dl>
      <p className="mt-4 text-xs text-text-muted">
        Vorlaeufige Diagnose — keine Netzanschlusszusage. Keine Kapazitätsgarantie.
      </p>
    </div>
  );
}

function ThermalScenarioTable({ szenarien }: { szenarien: Szenario[] }) {
  if (szenarien.length === 0) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10 text-text-dim">
            <th className="py-2 text-left">Szenario</th>
            <th className="py-2 text-right">Delta u</th>
            <th className="py-2 text-right">Trafo</th>
            <th className="py-2 text-right">Leitung</th>
            <th className="py-2 text-center">Status</th>
          </tr>
        </thead>
        <tbody>
          {szenarien.map((s) => (
            <tr key={s.name} className="border-b border-white/5">
              <td className="py-2 text-white">{s.name}</td>
              <td className="py-2 text-right text-text-muted">{s.delta_u_pct} %</td>
              <td className="py-2 text-right text-text-muted">{s.trafo_auslastung_pct} %</td>
              <td className="py-2 text-right text-text-muted">{s.leitung_auslastung_pct} %</td>
              <td className="py-2 text-center">
                <span className={`rounded-full px-2 py-0.5 text-xs ${statusClass(s.bewertung)}`}>{s.bewertung}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ScenarioComparePanel({ projectId, currentResult }: Props) {
  const [refresh, setRefresh] = useState(0);

  const snapshots = useMemo(() => {
    void refresh;
    const slots = getScenarioSlots(projectId);
    if (slots.A && slots.B) {
      return [slots.A, slots.B];
    }
    if (slots.A) {
      return [slots.A, slots.B].filter(Boolean) as ScenarioCompareSnapshot[];
    }
    const stored = listCompareSnapshots(projectId);
    if (stored.length >= 2) return stored;
    if (currentResult && stored.length === 0) {
      return [snapshotFromResult(currentResult, "Aktuelle Projektanalyse")];
    }
    return stored;
  }, [projectId, currentResult, refresh]);

  const left = snapshots[0] ?? getScenarioSlots(projectId).A ?? null;
  const right = snapshots[1] ?? getScenarioSlots(projectId).B ?? null;

  const [scenarioA, setScenarioA] = useState("");
  const [scenarioB, setScenarioB] = useState("");

  const sourceSzenarien = currentResult?.szenarien ?? left?.szenarien ?? [];
  const pickA = sourceSzenarien.find((s) => s.name === scenarioA) ?? sourceSzenarien[0];
  const pickB = sourceSzenarien.find((s) => s.name === scenarioB) ?? sourceSzenarien[1] ?? sourceSzenarien[0];

  return (
    <div className="space-y-8">
      <Card className="border-white/10 bg-surface/80">
        <CardHeader>
          <CardTitle className="text-white">Zwei gespeicherte Analysen</CardTitle>
          <CardDescription>
            Bis zu zwei Snapshots pro Projekt (Session). Nach jeder erfolgreichen Analyse wird der juengste Lauf
            automatisch gespeichert. Vollstaendige Server-History: siehe docs/SCENARIO_COMPARE.md.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <CompareColumn title="Slot A" snap={left} />
            <CompareColumn title="Slot B" snap={right} />
          </div>
          <Button
            type="button"
            variant="outline"
            className="border-white/15"
            onClick={() => {
              clearCompareSnapshots(projectId);
              setRefresh((n) => n + 1);
            }}
          >
            Snapshots loeschen
          </Button>
        </CardContent>
      </Card>

      {sourceSzenarien.length >= 2 ? (
        <Card className="border-white/10 bg-surface/80">
          <CardHeader>
            <CardTitle className="text-white">Zwei thermische Szenarien (eine Analyse)</CardTitle>
            <CardDescription>Vergleich innerhalb des aktuellen Ergebnisses — keine zweite Kapazitätsaussage.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-3 sm:flex-row">
              <label className="flex-1 text-sm text-text-muted">
                Szenario A
                <select
                  className="form-select mt-1 w-full cursor-pointer rounded-xl border border-border/70 bg-white/5 px-3 py-2 text-sm text-white focus:border-brand-cyan/70 focus:outline-none"
                  value={scenarioA || pickA?.name || ""}
                  onChange={(e) => setScenarioA(e.target.value)}
                >
                  {sourceSzenarien.map((s) => (
                    <option key={s.name} value={s.name}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex-1 text-sm text-text-muted">
                Szenario B
                <select
                  className="form-select mt-1 w-full cursor-pointer rounded-xl border border-border/70 bg-white/5 px-3 py-2 text-sm text-white focus:border-brand-cyan/70 focus:outline-none"
                  value={scenarioB || pickB?.name || ""}
                  onChange={(e) => setScenarioB(e.target.value)}
                >
                  {sourceSzenarien.map((s) => (
                    <option key={s.name} value={s.name}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {pickA && pickB ? (
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-xl border border-white/10 p-4">
                  <p className="font-medium text-white">{pickA.name}</p>
                  <p className="mt-2 text-sm text-text-muted">{pickA.beschreibung}</p>
                  <p className="mt-2 text-sm text-white/90">
                    Delta u: {pickA.delta_u_pct} % · Trafo {pickA.trafo_auslastung_pct} % · Leitung{" "}
                    {pickA.leitung_auslastung_pct} %
                  </p>
                </div>
                <div className="rounded-xl border border-white/10 p-4">
                  <p className="font-medium text-white">{pickB.name}</p>
                  <p className="mt-2 text-sm text-text-muted">{pickB.beschreibung}</p>
                  <p className="mt-2 text-sm text-white/90">
                    Delta u: {pickB.delta_u_pct} % · Trafo {pickB.trafo_auslastung_pct} % · Leitung{" "}
                    {pickB.leitung_auslastung_pct} %
                  </p>
                </div>
              </div>
            ) : null}
            <ThermalScenarioTable szenarien={sourceSzenarien} />
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
