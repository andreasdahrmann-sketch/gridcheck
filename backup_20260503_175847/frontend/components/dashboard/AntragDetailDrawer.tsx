"use client";

import React, { useEffect } from "react";
import { X, AlertTriangle, Sparkles, Network, Clock } from "lucide-react";
import type { Antrag, PrioResult } from "@/lib/priorisierung";
import { GEWICHTE } from "@/lib/priorisierung";

const TYPEN_LABEL: Record<string, string> = {
  solar: "☀️ Solar (PV)",
  wind: "💨 Wind",
  batterie: "🔋 Batteriespeicher",
  ladepark: "🚗 Ladepark",
  industrie: "🏭 Industrie",
  waermepumpe: "🌡️ Wärmepumpe",
  bhkw: "⚙️ BHKW",
  sonstige: "❓ Sonstige",
};

const REIFE_LABEL: Record<string, string> = {
  idee: "Idee",
  planung: "Planung",
  genehmigt: "Genehmigt",
  baubereit: "Baubereit",
};

function scoreColor(score: number): string {
  if (score >= 75) return "text-emerald-400";
  if (score >= 50) return "text-amber-400";
  return "text-rose-400";
}

function scoreBg(score: number): string {
  if (score >= 75) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-rose-500";
}

interface Props {
  open: boolean;
  onClose: () => void;
  antrag: Antrag | null;
  prio: PrioResult | null;
}

export default function AntragDetailDrawer({ open, onClose, antrag, prio }: Props) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open || !antrag || !prio) return null;
  const a = antrag;
  const p = prio;

  const beitragND = Math.round(p.netzdienlichkeit_score * GEWICHTE.netzdienlichkeit);
  const beitragWL = Math.round(p.warteliste_score * GEWICHTE.warteliste);
  const beitragDR = Math.round(p.dringlichkeit_score * GEWICHTE.dringlichkeit);
  const malus = p.dopplung_erkannt ? Math.round(GEWICHTE.dopplung_malus * 100) : 0;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Antragsdetails ${a.id}`}
        className="fixed top-0 right-0 h-full w-full max-w-xl bg-slate-900 border-l border-slate-700 shadow-2xl z-50 overflow-y-auto"
      >
        <div className="sticky top-0 bg-slate-900/95 backdrop-blur border-b border-slate-700 px-6 py-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500">Antrag</p>
            <h2 className="text-lg font-bold text-slate-100">{a.id}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-100"
            aria-label="Schließen"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="bg-slate-800/40 rounded-lg p-4 border border-slate-700 space-y-2">
            <h3 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-2">
              <Network className="w-4 h-4" /> Stammdaten
            </h3>
            <Row label="Antragsteller" value={a.antragsteller} />
            <Row label="Standort" value={`${a.plz} ${a.ort}`} />
            <Row label="Anlagentyp" value={TYPEN_LABEL[a.anlagentyp] ?? a.anlagentyp} />
            <Row label="Leistung" value={`${a.leistung_kw} kW`} />
            <Row label="Spannungsebene" value={a.spannungsebene} />
            <Row label="Eingangsdatum" value={a.eingangsdatum} />
            {a.foerderfrist && <Row label="Förderfrist" value={a.foerderfrist} />}
            <Row label="Projektreife" value={REIFE_LABEL[a.projektreife] ?? a.projektreife} />
            <Row label="Baugenehmigung" value={a.baugenehmigung_vorhanden ? "Ja" : "Nein"} />
            <Row label="Speicher" value={a.hat_speicher ? "Ja" : "Nein"} />
            <Row label="Blindleistung" value={a.hat_blindleistung ? "Ja" : "Nein"} />
            <Row label="Einspeisemanagement" value={a.hat_einspeisemanagement ? "Ja" : "Nein"} />
          </div>

          {p.dopplung_erkannt && (
            <div className="bg-rose-950/40 border border-rose-700/50 rounded-lg p-4 flex gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-rose-300">Mögliche Dopplung erkannt</p>
                <p className="text-xs text-rose-400/80 mt-1">
                  Ähnlicher Antrag vorhanden — bitte manuell prüfen. Malus: −{malus} Punkte.
                </p>
              </div>
            </div>
          )}

          <div className="bg-slate-800/40 rounded-lg p-4 border border-slate-700 space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <Sparkles className="w-4 h-4" /> Priorisierung
            </h3>
            <ScoreRow label="Netzdienlichkeit" raw={p.netzdienlichkeit_score} weightPct={Math.round(GEWICHTE.netzdienlichkeit*100)} contrib={beitragND} />
            <ScoreRow label="Warteliste" raw={p.warteliste_score} weightPct={Math.round(GEWICHTE.warteliste*100)} contrib={beitragWL} />
            <ScoreRow label="Dringlichkeit" raw={p.dringlichkeit_score} weightPct={Math.round(GEWICHTE.dringlichkeit*100)} contrib={beitragDR} />
            {p.dopplung_erkannt && (
              <div className="flex items-center justify-between text-xs text-rose-400">
                <span>Malus Dopplung</span>
                <span className="font-mono">−{malus}</span>
              </div>
            )}
            <div className="flex items-center justify-between text-sm pt-2 border-t border-slate-700">
              <span className="text-slate-300 font-semibold">Gesamt</span>
              <span className={`font-mono font-bold ${scoreColor(p.gesamt_score)}`}>
                {p.gesamt_score}
              </span>
            </div>
          </div>

          {p.hinweise.length > 0 && (
            <div className="bg-slate-800/40 rounded-lg p-4 border border-slate-700">
              <h3 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-2">
                <Clock className="w-4 h-4" /> Hinweise
              </h3>
              <ul className="space-y-1">
                {p.hinweise.map((h, i) => (
                  <li key={i} className="text-xs text-slate-400">💡 {h}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="bg-slate-800/20 rounded-lg p-4 border border-dashed border-slate-700 text-center">
            <p className="text-xs text-slate-500">
              Aktionen (Status ändern, Notiz, PDF-Export) folgen im nächsten Meilenstein.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-400">{label}</span>
      <span className="text-slate-200 font-medium">{value}</span>
    </div>
  );
}

function ScoreRow({
  label, raw, weightPct, contrib,
}: { label: string; raw: number; weightPct: number; contrib: number }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-slate-300">{label}</span>
        <span className="text-xs text-slate-500">Gewicht {weightPct}%</span>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex-1 bg-slate-700 rounded-full h-1.5 overflow-hidden">
          <div className={`h-full ${scoreBg(raw)}`} style={{ width: `${raw}%` }} />
        </div>
        <div className="text-xs font-mono text-slate-400 w-20 text-right">
          {raw} → +{contrib}
        </div>
      </div>
    </div>
  );
}
