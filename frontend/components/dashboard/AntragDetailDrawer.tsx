"use client";

import React, { useEffect, useState } from "react";
import { X, AlertTriangle, Network, Clock, FileText, Shield, ShieldAlert } from "lucide-react";
import type { Antrag, PrioResult } from "@/lib/priorisierung";
import { GEWICHTE } from "@/lib/priorisierung";
import {
  type AntragStatus,
  type AuditEntry,
  STATUS_LABEL,
  getMeta,
  getAuditTrail,
  setStatus,
  setNote,
  verifyAuditChain,
} from "@/lib/antragStore";

const TYPEN_LABEL: Record<string, string> = {
  solar: "PV",
  wind: "Wind",
  batterie: "Batteriespeicher",
  ladepark: "Ladepark",
  waermepumpe: "Waermepumpe",
  sonstiges: "Sonstiges",
};

const REIFE_LABEL: Record<string, string> = {
  idee: "Idee",
  planung: "Planung",
  genehmigt: "Genehmigt",
  baubereit: "Baubereit",
};

const ACTION_LABEL: Record<string, string> = {
  created: "Angelegt",
  status_changed: "Status geaendert",
  note_added: "Notiz hinzugefuegt",
  note_updated: "Notiz geaendert",
};

const STATUS_OPTIONS: AntragStatus[] = [
  "eingegangen",
  "in_pruefung",
  "rueckfrage",
  "genehmigt",
  "abgelehnt",
];

const CURRENT_USER = "netzbetreiber@demo";

interface Props {
  antrag: Antrag | null;
  prio: PrioResult | null;
  onClose: () => void;
  onChanged?: () => void;
}

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

function formatTs(iso: string): string {
  try {
    return new Date(iso).toLocaleString("de-DE");
  } catch {
    return iso;
  }
}

export default function AntragDetailDrawer({ antrag, prio, onClose, onChanged }: Props) {
  const [status, setStatusState] = useState<AntragStatus>("eingegangen");
  const [note, setNoteState] = useState<string>("");
  const [statusComment, setStatusComment] = useState<string>("");
  const [auditTrail, setAuditTrail] = useState<AuditEntry[]>([]);
  const [chainValid, setChainValid] = useState<boolean>(true);

  useEffect(() => {
    if (!antrag) return;
    const meta = getMeta(antrag.id);
    setStatusState(meta.status);
    setNoteState(meta.note);
    setStatusComment("");
    const trail = getAuditTrail(antrag.id);
    setAuditTrail(trail);
    setChainValid(verifyAuditChain(antrag.id).valid);
  }, [antrag]);

  if (!antrag) return null;

  const handleStatusSave = () => {
    setStatus(antrag.id, status, statusComment, CURRENT_USER);
    setStatusComment("");
    setAuditTrail(getAuditTrail(antrag.id));
    setChainValid(verifyAuditChain(antrag.id).valid);
    onChanged?.();
  };

  const handleNoteSave = () => {
    setNote(antrag.id, note, CURRENT_USER);
    setAuditTrail(getAuditTrail(antrag.id));
    setChainValid(verifyAuditChain(antrag.id).valid);
    onChanged?.();
  };

  const komponenten: Array<{ label: string; score: number; gewicht: number }> = prio
    ? [
        { label: "Netzdienlichkeit", score: prio.netzdienlichkeit_score, gewicht: GEWICHTE.netzdienlichkeit },
        { label: "Warteliste", score: prio.warteliste_score, gewicht: GEWICHTE.warteliste },
        { label: "Dringlichkeit", score: prio.dringlichkeit_score, gewicht: GEWICHTE.dringlichkeit },
      ]
    : [];

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/60" onClick={onClose} />
      <div className="w-full max-w-2xl bg-slate-900 border-l border-slate-700 overflow-y-auto">
        <div className="sticky top-0 bg-slate-900 border-b border-slate-700 p-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Antrag {antrag.id}</h2>
            <p className="text-sm text-slate-400">{antrag.antragsteller}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded">
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        <div className="p-4 space-y-6">
          {/* Stammdaten */}
          <section>
            <h3 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-2">
              <FileText className="w-4 h-4" /> Stammdaten
            </h3>
            <dl className="grid grid-cols-2 gap-2 text-sm">
              <dt className="text-slate-500">Anlagentyp</dt>
              <dd className="text-slate-200">{TYPEN_LABEL[antrag.anlagentyp] ?? antrag.anlagentyp}</dd>
              <dt className="text-slate-500">Leistung</dt>
              <dd className="text-slate-200">{antrag.leistung_kw} kW</dd>
              <dt className="text-slate-500">Spannungsebene</dt>
              <dd className="text-slate-200">{antrag.spannungsebene}</dd>
              <dt className="text-slate-500">Projektreife</dt>
              <dd className="text-slate-200">{REIFE_LABEL[antrag.projektreife] ?? antrag.projektreife}</dd>
              <dt className="text-slate-500">Eingang</dt>
              <dd className="text-slate-200">{antrag.eingangsdatum}</dd>
              <dt className="text-slate-500">Standort</dt>
              <dd className="text-slate-200">{antrag.plz} {antrag.ort ?? ""}</dd>
              {antrag.max_export_kw !== undefined && (
                <>
                  <dt className="text-slate-500">NAP Export</dt>
                  <dd className="text-slate-200">{antrag.max_export_kw} kW</dd>
                </>
              )}
              {antrag.max_import_kw !== undefined && (
                <>
                  <dt className="text-slate-500">NAP Bezug</dt>
                  <dd className="text-slate-200">{antrag.max_import_kw} kW</dd>
                </>
              )}
              {antrag.storage_operation_mode && (
                <>
                  <dt className="text-slate-500">Speicherbetrieb</dt>
                  <dd className="text-slate-200">{antrag.storage_operation_mode}</dd>
                </>
              )}
              {antrag.route_risk_level && (
                <>
                  <dt className="text-slate-500">Umwelt / Trasse</dt>
                  <dd className="text-slate-200">{antrag.route_risk_level}</dd>
                </>
              )}
              {antrag.stakeholder_konflikt_level && (
                <>
                  <dt className="text-slate-500">Stakeholder-Konflikt</dt>
                  <dd className="text-slate-200">{antrag.stakeholder_konflikt_level}</dd>
                </>
              )}
              {antrag.gridcheck_score !== undefined && (
                <>
                  <dt className="text-slate-500">GridCheck-Score</dt>
                  <dd className={scoreColor(antrag.gridcheck_score)}>{antrag.gridcheck_score}</dd>
                </>
              )}
            </dl>
          </section>

          {/* Priorisierung */}
          {prio && (
            <section>
              <h3 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-2">
                <Network className="w-4 h-4" /> Priorisierung
              </h3>
              <div className="bg-slate-800/60 rounded p-3 mb-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-slate-400 text-sm">Gesamt-Score (Rang {prio.rang})</span>
                  <span className={`text-2xl font-bold ${scoreColor(prio.gesamt_score)}`}>{prio.gesamt_score}</span>
                </div>
                <div className="w-full bg-slate-700 rounded h-2">
                  <div className={`h-2 rounded ${scoreBg(prio.gesamt_score)}`} style={{ width: `${prio.gesamt_score}%` }} />
                </div>
              </div>

              <div className="space-y-2">
                {komponenten.map((k) => (
                  <div key={k.label}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-400">{k.label} <span className="text-slate-600">(Gewicht {Math.round(k.gewicht * 100)}%)</span></span>
                      <span className={scoreColor(k.score)}>{k.score}</span>
                    </div>
                    <div className="w-full bg-slate-700 rounded h-1.5">
                      <div className={`h-1.5 rounded ${scoreBg(k.score)}`} style={{ width: `${k.score}%` }} />
                    </div>
                  </div>
                ))}
              </div>

              {prio.dopplung_erkannt && (
                <div className="mt-3 flex items-start gap-2 bg-rose-950/40 border border-rose-800 rounded p-2 text-xs text-rose-300">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold">Dopplung erkannt</div>
                    <div>Mit Antrag/Antraegen: {prio.dopplung_ids.join(", ")}</div>
                  </div>
                </div>
              )}

              {prio.hinweise.length > 0 && (
                <ul className="mt-3 space-y-1 text-xs text-slate-400">
                  {prio.hinweise.map((h, i) => (
                    <li key={i} className="flex gap-2"><span className="text-cyan-500">•</span><span>{h}</span></li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {/* Status */}
          <section>
            <h3 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-2">
              <Clock className="w-4 h-4" /> Status
            </h3>
            <div className="space-y-2">
              <select
                value={status}
                onChange={(e) => setStatusState(e.target.value as AntragStatus)}
                className="form-select w-full cursor-pointer rounded-xl border border-border/70 bg-white/5 px-3 py-2 text-sm text-white focus:border-brand-cyan/70 focus:outline-none"
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>{STATUS_LABEL[s]}</option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Kommentar (optional)"
                value={statusComment}
                onChange={(e) => setStatusComment(e.target.value)}
                className="form-select w-full cursor-pointer rounded-xl border border-border/70 bg-white/5 px-3 py-2 text-sm text-white focus:border-brand-cyan/70 focus:outline-none"
              />
              <button
                onClick={handleStatusSave}
                className="w-full bg-cyan-600 hover:bg-cyan-500 text-white rounded px-3 py-2 text-sm font-medium"
              >
                Status speichern
              </button>
            </div>
          </section>

          {/* Notiz */}
          <section>
            <h3 className="text-sm font-semibold text-slate-300 mb-2">Interne Notiz</h3>
            <textarea
              value={note}
              onChange={(e) => setNoteState(e.target.value)}
              rows={4}
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-white"
              placeholder="Notizen, Rueckfragen, interne Hinweise ..."
            />
            <button
              onClick={handleNoteSave}
              className="mt-2 w-full bg-slate-700 hover:bg-slate-600 text-white rounded px-3 py-2 text-sm font-medium"
            >
              Notiz speichern
            </button>
          </section>

          {/* Audit Trail */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-slate-300">Audit-Trail</h3>
              {chainValid ? (
                <div className="flex items-center gap-1 text-xs text-emerald-400">
                  <Shield className="w-3 h-3" />
                  <span>Chain gueltig</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 text-xs text-rose-400">
                  <ShieldAlert className="w-3 h-3" />
                  <span>Chain UNGUELTIG</span>
                </div>
              )}
            </div>
            {auditTrail.length === 0 ? (
              <p className="text-sm text-slate-500 italic">Noch keine Eintraege.</p>
            ) : (
              <ol className="space-y-2 max-h-64 overflow-y-auto">
                {auditTrail.slice().reverse().map((e) => (
                  <li key={e.id} className="text-xs border-l-2 border-slate-700 pl-3 py-1">
                    <div className="flex items-center justify-between">
                      <span className="text-cyan-400 font-medium">{ACTION_LABEL[e.action] ?? e.action}</span>
                      <span className="text-slate-500">{formatTs(e.timestamp)}</span>
                    </div>
                    <div className="text-slate-400 mt-0.5">
                      {e.old_value !== null && e.new_value !== null && (
                        <span>{e.old_value} -&gt; {e.new_value}</span>
                      )}
                      {e.old_value === null && e.new_value !== null && (
                        <span>{e.new_value}</span>
                      )}
                      {e.comment && <span className="italic"> &quot;{e.comment}&quot;</span>}
                    </div>
                    <div className="text-slate-600 mt-0.5">von {e.user} · hash {e.hash}</div>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
