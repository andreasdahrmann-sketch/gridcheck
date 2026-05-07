"use client";
import { useState } from "react";
import type { GridCheckInput, GridCheckResult, Spannungsebene, Topologie } from "../types";
import VnbBanner from "./VnbBanner";
import { analyzeGridcheck, AnalyzeApiError } from "../lib/api/analyze";

type CustomerType = "projektierer" | "speicherbetreiber" | "netzbetreiber";

const CUSTOMER_LABELS: Record<CustomerType, string> = {
  projektierer: "Projektierer / EPC",
  speicherbetreiber: "Speicher- / Parkbetreiber",
  netzbetreiber: "Netzbetreiber",
};

const CUSTOMER_DESC: Record<CustomerType, string> = {
  projektierer: "Prüfung ob Netzanschluss technisch machbar ist.",
  speicherbetreiber: "Bewertung inkl. Speicherdimensionierung.",
  netzbetreiber: "N-1 Analyse, Engpasserkennung, Kapazitätsbewertung.",
};

const ERZEUGUNGS_OPTIONEN: Record<CustomerType, string[]> = {
  projektierer: ["PV", "Wind", "PV + Speicher", "Wind + Speicher", "Hybridpark"],
  speicherbetreiber: ["BESS", "PV + Speicher", "Wind + Speicher", "Hybridpark"],
  netzbetreiber: ["Alle Einspeiser", "PV-Park", "Windpark", "BESS", "Mischgebiet"],
};

interface MetaData {
  kundentyp: CustomerType | "";
  projektname: string;
  ort: string;
  erzeugungstyp: string;
}

const INITIAL_INPUT: GridCheckInput = {
  anlagentyp: "solar" as const,
  anschlussleistung_kw: 5000,
  spannungsebene: "MS" as Spannungsebene,
  cos_phi: 0.95,
  richtung: "einspeisung",
  plz: "30159",
  topologie: "unbekannt" as Topologie,
};

const INITIAL_META: MetaData = {
  kundentyp: "",
  projektname: "",
  ort: "",
  erzeugungstyp: "",
};

export default function GridCheckForm() {
  const [step, setStep] = useState(0);
  const [input, setInput] = useState<GridCheckInput>({ ...INITIAL_INPUT });
  const [meta, setMeta] = useState<MetaData>({ ...INITIAL_META });
  const [result, setResult] = useState<GridCheckResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const ct = meta.kundentyp as CustomerType;

  const updateInput = (patch: Partial<GridCheckInput>) => setInput(prev => ({ ...prev, ...patch }));
  const updateMeta = (patch: Partial<MetaData>) => setMeta(prev => ({ ...prev, ...patch }));

  const runAnalysis = async () => {
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const r = await analyzeGridcheck(input);
      setResult(r);
      setStep(2);
    } catch (err) {
      if (err instanceof AnalyzeApiError) {
        setAnalysisError(err.message);
      } else {
        setAnalysisError("Analyse konnte nicht gestartet werden.");
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const sectionClass = "bg-gray-800/60 border border-gray-700 rounded-xl p-5";
  const sectionTitle = "text-lg font-semibold text-white mb-3";
  const labelClass = "block text-sm text-gray-300 mb-1";
  const inputClass = "w-full bg-gray-900 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none";
  const selectClass = inputClass;

  // ==================== STEP 0: Kundentyp ====================
  if (step === 0) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <h2 className="text-2xl font-bold text-white text-center">Wählen Sie Ihren Anwendungsfall</h2>
        <div className="grid md:grid-cols-3 gap-4">
          {(Object.keys(CUSTOMER_LABELS) as CustomerType[]).map((key) => (
            <button key={key} onClick={() => { updateMeta({ kundentyp: key }); setStep(1); }}
              className="bg-gray-800/60 border border-gray-700 hover:border-blue-500 rounded-xl p-6 text-left transition group">
              <div className="text-lg font-semibold text-white group-hover:text-blue-400 mb-2">{CUSTOMER_LABELS[key]}</div>
              <div className="text-sm text-gray-400">{CUSTOMER_DESC[key]}</div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // ==================== STEP 1: Eingaben ====================
  if (step === 1) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-white">Netzanschluss-Analyse</h2>
          <span className="text-sm text-gray-400 bg-gray-800 px-3 py-1 rounded-full">{CUSTOMER_LABELS[ct]}</span>
        </div>

        {/* Projektdaten */}
        <div className={sectionClass}>
          <h3 className={sectionTitle}>Projektdaten</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Projektname</label>
              <input className={inputClass} value={meta.projektname} onChange={e => updateMeta({ projektname: e.target.value })} placeholder="z.B. Solarpark Musterstadt" />
            </div>
            <div>
              <label className={labelClass}>PLZ</label>
              <input className={inputClass} value={input.plz} onChange={e => updateInput({ plz: e.target.value })} placeholder="z.B. 30159" maxLength={5} inputMode="numeric" />
            </div>
            <div>
              <label className={labelClass}>Ort</label>
              <input className={inputClass} value={meta.ort} onChange={e => updateMeta({ ort: e.target.value })} placeholder="z.B. Hannover" />
            </div>
            <div>
              <label className={labelClass}>Erzeugungstyp</label>
              <select className={selectClass} value={meta.erzeugungstyp} onChange={e => updateMeta({ erzeugungstyp: e.target.value })}>
                <option value="">-- Wählen --</option>
                {ERZEUGUNGS_OPTIONEN[ct]?.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          </div>
          <VnbBanner plz={input.plz} />
        </div>

        {/* Technische Daten */}
        <div className={sectionClass}>
          <h3 className={sectionTitle}>Technische Parameter</h3>
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <label className={labelClass}>Anschlussleistung (kW)</label>
              <input type="number" className={inputClass} value={input.anschlussleistung_kw} onChange={e => updateInput({ anschlussleistung_kw: Number(e.target.value) })} />
            </div>
            <div>
              <label className={labelClass}>Spannungsebene</label>
              <select className={selectClass} value={input.spannungsebene} onChange={e => updateInput({ spannungsebene: e.target.value as Spannungsebene })}>
                <option value="NS">NS (0,4 kV)</option>
                <option value="MS">MS (20 kV)</option>
                <option value="HS">HS (110 kV)</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>cos phi</label>
              <input type="number" step="0.01" min="0.8" max="1" className={inputClass} value={input.cos_phi} onChange={e => updateInput({ cos_phi: Number(e.target.value) })} />
            </div>
            <div>
              <label className={labelClass}>Richtung</label>
              <select className={selectClass} value={input.richtung} onChange={e => updateInput({ richtung: e.target.value as GridCheckInput["richtung"] })}>
                <option value="einspeisung">Einspeisung</option>
                <option value="bezug">Bezug</option>
                <option value="bidirektional">Bidirektional</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>Topologie</label>
              <select className={selectClass} value={input.topologie ?? "unbekannt"} onChange={e => updateInput({ topologie: e.target.value as Topologie })}>
                <option value="radial">Radial</option>
                <option value="ring">Ring</option>
                <option value="vermascht">Vermascht</option>
                <option value="unbekannt">Unbekannt</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>Entfernung NVP (km)</label>
              <input type="number" step="0.1" className={inputClass} value={input.entfernung_km ?? ""} onChange={e => updateInput({ entfernung_km: e.target.value ? Number(e.target.value) : undefined })} placeholder="auto" />
            </div>
          </div>
        </div>

        {/* Optionale Netzdaten */}
        <div className={sectionClass}>
          <h3 className={sectionTitle}>Netzdaten (optional - erhoehen Genauigkeit)</h3>
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <label className={labelClass}>Sk min (MVA)</label>
              <input type="number" step="1" className={inputClass} value={input.sk_min_mva ?? ""} onChange={e => updateInput({ sk_min_mva: e.target.value ? Number(e.target.value) : undefined })} placeholder="auto" />
            </div>
            <div>
              <label className={labelClass}>Sk max (MVA)</label>
              <input type="number" step="1" className={inputClass} value={input.sk_max_mva ?? ""} onChange={e => updateInput({ sk_max_mva: e.target.value ? Number(e.target.value) : undefined })} placeholder="auto" />
            </div>
            <div>
              <label className={labelClass}>R/X Verhaeltnis</label>
              <input type="number" step="0.1" className={inputClass} value={input.rx_verhaeltnis ?? ""} onChange={e => updateInput({ rx_verhaeltnis: e.target.value ? Number(e.target.value) : undefined })} placeholder="auto" />
            </div>
            <div>
              <label className={labelClass}>Trafo Sr (kVA)</label>
              <input type="number" className={inputClass} value={input.trafo_sr_kva ?? ""} onChange={e => updateInput({ trafo_sr_kva: e.target.value ? Number(e.target.value) : undefined })} placeholder="auto" />
            </div>
            <div>
              <label className={labelClass}>Trafo uk (%)</label>
              <input type="number" step="0.1" className={inputClass} value={input.trafo_uk_pct ?? ""} onChange={e => updateInput({ trafo_uk_pct: e.target.value ? Number(e.target.value) : undefined })} placeholder="auto" />
            </div>
            <div>
              <label className={labelClass}>Freie Kapazität (kW)</label>
              <input type="number" className={inputClass} value={input.netzkapazitaet_kw ?? ""} onChange={e => updateInput({ netzkapazitaet_kw: e.target.value ? Number(e.target.value) : undefined })} placeholder="auto" />
            </div>
          </div>
        </div>

        {analysisError && (
          <div className="bg-red-900/30 border border-red-700 rounded-xl p-3 text-sm text-red-200">
            {analysisError}
          </div>
        )}

        {/* Buttons */}
        <div className="flex justify-between pt-4">
          <button onClick={() => setStep(0)} className="text-gray-400 hover:text-white border border-gray-600 px-6 py-2.5 rounded-lg text-sm transition">Zurueck</button>
          <button
            onClick={runAnalysis}
            disabled={isAnalyzing}
            className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:opacity-60 disabled:cursor-not-allowed text-white px-8 py-2.5 rounded-lg text-sm font-semibold transition"
          >
            {isAnalyzing ? "Analyse laeuft..." : "Analyse starten"}
          </button>
        </div>
      </div>
    );
  }

  // ==================== STEP 2: Ergebnis ====================
  if (step === 2 && result) {
    const scoreColor = result.score >= 70 ? "text-green-400" : result.score >= 50 ? "text-yellow-400" : result.score >= 30 ? "text-orange-400" : "text-red-400";
    const stufeLabels: Record<string, string> = { gruen: "Machbar", gelb: "Bedingt machbar", orange: "Eingeschraenkt", rot: "Kritisch" };
    const stufeColors: Record<string, string> = { gruen: "bg-green-600", gelb: "bg-yellow-600", orange: "bg-orange-600", rot: "bg-red-600" };

    return (
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white mb-2">Ergebnis: {meta.projektname || "Netzanschluss-Analyse"}</h2>
          <div className="flex justify-center gap-3 items-center">
            <span className={`${stufeColors[result.machbarkeit_stufe]} px-4 py-1 rounded-full text-white text-sm font-semibold`}>{stufeLabels[result.machbarkeit_stufe]}</span>
            <span className={`text-3xl font-bold ${scoreColor}`}>{result.score}/100</span>
            <span className="text-gray-400 text-sm">Confidence: {result.daten_confidence}</span>
          </div>
        </div>

        {/* Kerndaten */}
        <div className={sectionClass}>
          <h3 className={sectionTitle}>Kerndaten</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">P</div><div className="text-white font-mono text-lg">{result.p_max_kW} kW</div></div>
            <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">S</div><div className="text-white font-mono text-lg">{result.s_max_kVA} kVA</div></div>
            <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">I Betrieb</div><div className="text-white font-mono text-lg">{result.i_betrieb_A} A</div></div>
            <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Delta u</div><div className="text-white font-mono text-lg">{result.delta_u_pct}%</div></div>
          </div>
        </div>

        {/* Teil-Scores */}
        <div className={sectionClass}>
          <h3 className={sectionTitle}>Bewertung</h3>
          <div className="space-y-2">
            {[
              { label: "Kapazität", val: result.teil_scores.kapazitaet, max: 25 },
              { label: "Spannung", val: result.teil_scores.spannung, max: 25 },
              { label: "Kurzschluss", val: result.teil_scores.kurzschluss, max: 20 },
              { label: "N-1 Sicherheit", val: result.teil_scores.n1, max: 15 },
              { label: "Datenqualitaet", val: result.teil_scores.datenqualitaet, max: 15 },
            ].map(s => (
              <div key={s.label} className="flex items-center gap-3">
                <div className="w-32 text-sm text-gray-300">{s.label}</div>
                <div className="flex-1 bg-gray-900 rounded-full h-3 overflow-hidden">
                  <div className={`h-full rounded-full ${s.val / s.max > 0.7 ? "bg-green-500" : s.val / s.max > 0.4 ? "bg-yellow-500" : "bg-red-500"}`} style={{ width: `${(s.val / s.max) * 100}%` }} />
                </div>
                <div className="text-sm text-gray-400 w-12 text-right">{s.val}/{s.max}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Szenarien */}
        <div className={sectionClass}>
          <h3 className={sectionTitle}>Szenarien-Analyse</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-gray-400 border-b border-gray-700">
                <th className="text-left py-2">Szenario</th><th className="text-right">Delta u (%)</th><th className="text-right">Trafo (%)</th><th className="text-right">Leitung (%)</th><th className="text-right">Ik (kA)</th><th className="text-center">Status</th>
              </tr></thead>
              <tbody>
                {result.szenarien.map(s => (
                  <tr key={s.name} className="border-b border-gray-800">
                    <td className="py-2 text-white">{s.name}</td>
                    <td className="text-right text-gray-300">{s.delta_u_pct}</td>
                    <td className="text-right text-gray-300">{s.trafo_auslastung_pct}</td>
                    <td className="text-right text-gray-300">{s.leitung_auslastung_pct}</td>
                    <td className="text-right text-gray-300">{s.ik_kA}</td>
                    <td className="text-center">
                      <span className={`px-2 py-0.5 rounded text-xs ${s.bewertung === "ok" ? "bg-green-900 text-green-300" : s.bewertung === "grenzwertig" ? "bg-yellow-900 text-yellow-300" : "bg-red-900 text-red-300"}`}>{s.bewertung}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* N-1 */}
        <div className={sectionClass}>
          <h3 className={sectionTitle}>N-1 Analyse</h3>
          <div className="flex items-center gap-3 mb-2">
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${result.n1_prescreen_ok ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>{result.n1_prescreen_ok ? "Bestanden" : "Nicht bestanden"}</span>
          </div>
          <p className="text-gray-300 text-sm">{result.n1_prescreen_detail}</p>
          <p className="text-gray-400 text-xs mt-1">{result.n1_hinweis}</p>
        </div>

        {/* Kurzschluss */}
        <div className={sectionClass}>
          <h3 className={sectionTitle}>Kurzschluss</h3>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Ik min</div><div className="text-white font-mono">{result.kurzschluss.ik_min_kA} kA</div></div>
            <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Ik max</div><div className="text-white font-mono">{result.kurzschluss.ik_max_kA} kA</div></div>
            <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Sk am NVP</div><div className="text-white font-mono">{result.kurzschluss.sk_am_nvp_mva} MVA</div></div>
          </div>
          <p className="text-sm text-gray-400 mt-2">{result.kurzschluss.bewertung}</p>
        </div>

        {/* Kosten und Empfehlungen */}
        <div className="grid md:grid-cols-2 gap-4">
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Kosten / Zeit</h3>
            <div className="space-y-2 text-sm text-gray-300">
              <p>Indikation: <span className="text-white font-semibold">{result.kosten_indikation_eur.toLocaleString("de-DE")} EUR</span></p>
              <p>Kostenklasse: {result.kostenklasse}</p>
              <p>Bearbeitungszeit: ca. {result.geschaetzte_bearbeitungszeit_wochen} Wochen</p>
              <p>Netzausbau: {result.netzausbau_erforderlich ? "Ja" : "Nein"}</p>
            </div>
          </div>
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Empfehlungen</h3>
            <ul className="space-y-1 text-sm text-gray-300">
              {result.empfehlungen.map((e, i) => <li key={i} className="flex gap-2"><span className="text-blue-400">&#8226;</span>{e}</li>)}
            </ul>
          </div>
        </div>

        {/* Impedanzen */}
        <div className={sectionClass}>
          <h3 className={sectionTitle}>Impedanzmodell</h3>
          <div className="grid grid-cols-4 gap-3">
            <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Z Quelle</div><div className="text-white font-mono">{result.z_quelle_ohm} Ohm</div></div>
            <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Z Trafo</div><div className="text-white font-mono">{result.z_trafo_ohm} Ohm</div></div>
            <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Z Leitung</div><div className="text-white font-mono">{result.z_leitung_ohm} Ohm</div></div>
            <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Z Gesamt</div><div className="text-white font-mono">{result.z_gesamt_ohm} Ohm</div></div>
          </div>
        </div>

        {/* Einschraenkungen */}
        {result.einschraenkungen.length > 0 && (
          <div className="bg-yellow-900/30 border border-yellow-700 rounded-xl p-4">
            <h4 className="text-yellow-400 font-semibold text-sm mb-2">Einschraenkungen</h4>
            <ul className="text-sm text-yellow-200 space-y-1">
              {result.einschraenkungen.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          </div>
        )}

        {/* Buttons */}
        <div className="flex justify-between items-center pt-4">
          <button onClick={() => setStep(1)} className="text-gray-400 hover:text-white border border-gray-600 px-6 py-2.5 rounded-lg text-sm transition">Eingaben bearbeiten</button>
          <div className="flex gap-3">
            <button onClick={() => { setStep(0); setInput({ ...INITIAL_INPUT }); setMeta({ ...INITIAL_META }); setResult(null); }}
              className="border border-gray-600 text-gray-300 hover:text-white px-6 py-2.5 rounded-lg text-sm transition">Neue Analyse</button>
            <button className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-2.5 rounded-lg text-sm font-semibold transition">PDF Export</button>
          </div>
        </div>

        <div className="mt-6 border-t border-gray-700 pt-4 text-center text-gray-500 text-xs">
          Analyse-ID: GC-{Date.now().toString(36).toUpperCase()} | {new Date().toLocaleString("de-DE")} | Revisionssicher | Keine Gewaehr
        </div>
      </div>
    );
  }

  return null;
}

