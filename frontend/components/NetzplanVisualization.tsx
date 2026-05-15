"use client";

import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  BatteryCharging,
  Factory,
  Gauge,
  Info,
  Network,
  Route,
  ShieldAlert,
  ShieldCheck,
  SunMedium,
  Wind,
  Workflow,
} from "lucide-react";
import NetzplanMapPanel from "@/components/netzplan/NetzplanMapPanel";
import type { GridCheckInput, GridCheckResult } from "@/types";

type Tone = "good" | "warn" | "critical" | "neutral";

interface VisualizationMeta {
  kundentyp?: string;
  projektname?: string;
  ort?: string;
  erzeugungstyp?: string;
}

interface NetzplanVisualizationProps {
  input: GridCheckInput;
  result: GridCheckResult;
  meta?: VisualizationMeta;
}

interface PlanBadge {
  label: string;
  tone: Tone;
}

interface ScoreMetric {
  label: string;
  value: number;
  tone: Tone;
}

interface RawMetric {
  label: string;
  value: string;
  detail: string;
  tone: Tone;
}

interface ProjectComponentChip {
  label: string;
  tone: Tone;
  icon: LucideIcon;
}

interface RiskNote {
  title: string;
  body: string;
  tone: Tone;
  icon: LucideIcon;
}

const TONE_STYLES: Record<
  Tone,
  {
    badge: string;
    panel: string;
    text: string;
    line: string;
    dot: string;
  }
> = {
  good: {
    badge: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
    panel: "border-emerald-400/20 bg-emerald-500/10",
    text: "text-emerald-300",
    line: "#5FD0B8",
    dot: "bg-emerald-400",
  },
  warn: {
    badge: "border-amber-400/30 bg-amber-500/10 text-amber-100",
    panel: "border-amber-400/20 bg-amber-500/10",
    text: "text-amber-200",
    line: "#F59E0B",
    dot: "bg-amber-400",
  },
  critical: {
    badge: "border-rose-400/30 bg-rose-500/10 text-rose-100",
    panel: "border-rose-400/20 bg-rose-500/10",
    text: "text-rose-200",
    line: "#F87171",
    dot: "bg-rose-400",
  },
  neutral: {
    badge: "border-cyan-400/30 bg-cyan-500/10 text-cyan-100",
    panel: "border-cyan-400/20 bg-cyan-500/10",
    text: "text-cyan-100",
    line: "#79E0C4",
    dot: "bg-cyan-300",
  },
};

const MACHBARKEIT_LABELS: Record<GridCheckResult["machbarkeit_stufe"], string> = {
  gruen: "Machbar",
  gelb: "Bedingt machbar",
  orange: "Eingeschraenkt",
  rot: "Kritisch",
};

const SPANNUNG_LABELS: Record<GridCheckInput["spannungsebene"], string> = {
  NS: "NS / 0,4 kV",
  MS: "MS / 20 kV",
  HS: "HS / 110 kV",
};

const TOPOLOGIE_LABELS: Record<GridCheckInput["topologie"], string> = {
  radial: "Radial",
  ring: "Ring",
  stich: "Stich",
  stich_mit_notverbindung: "Stich mit Notverbindung",
  ring_offen: "Ring offen",
  ring_geschlossen: "Ring geschlossen",
  doppelstich: "Doppelstich",
  vermascht: "Vermascht",
  unbekannt: "Topologie offen",
};

const RICHTUNG_LABELS: Record<GridCheckInput["richtung"], string> = {
  einspeisung: "Einspeisung",
  bezug: "Entnahme",
  bidirektional: "Bidirektional",
};

const ANLAGENTYP_LABELS: Record<GridCheckInput["anlagentyp"], string> = {
  solar: "PV",
  wind: "Wind",
  batterie: "BESS",
  waermepumpe: "Waermepumpe",
  ladepark: "Ladepark",
  sonstiges: "Projektanlage",
};

const KUNDENTYP_LABELS: Record<string, string> = {
  projektierer: "Projektierer / EPC",
  speicherbetreiber: "Speicherbetreiber",
  netzbetreiber: "Netzbetreiber",
  investor: "Investor",
};

function formatNumber(value: number, digits = 0): string {
  return new Intl.NumberFormat("de-DE", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

function clampPercent(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, value));
}

function pickPositive(...values: Array<number | undefined>): number | null {
  for (const value of values) {
    if (typeof value === "number" && Number.isFinite(value) && value > 0) {
      return value;
    }
  }
  return null;
}

function uniq(values: Array<string | undefined | null>): string[] {
  const seen = new Set<string>();
  const output: string[] = [];

  values.forEach((value) => {
    const trimmed = value?.trim();
    if (!trimmed || seen.has(trimmed)) return;
    seen.add(trimmed);
    output.push(trimmed);
  });

  return output;
}

function toneFromScore(value: number): Tone {
  if (value >= 70) return "good";
  if (value >= 45) return "warn";
  return "critical";
}

function toneFromUtilization(value: number): Tone {
  if (value >= 100) return "critical";
  if (value >= 80) return "warn";
  if (value > 0) return "good";
  return "neutral";
}

function toneFromRouteLevel(level: GridCheckResult["route_environment"]["risk_level"]): Tone {
  if (level === "hoch") return "critical";
  if (level === "mittel") return "warn";
  return "good";
}

function toneFromMachbarkeit(stufe: GridCheckResult["machbarkeit_stufe"]): Tone {
  if (stufe === "gruen") return "good";
  if (stufe === "gelb" || stufe === "orange") return "warn";
  return "critical";
}

function componentIcon(label: string): LucideIcon {
  const value = label.toLowerCase();
  if (value.includes("wind")) return Wind;
  if (value.includes("bess") || value.includes("speicher") || value.includes("battery")) {
    return BatteryCharging;
  }
  if (value.includes("pv") || value.includes("solar")) return SunMedium;
  return Factory;
}

function componentTone(label: string): Tone {
  const value = label.toLowerCase();
  if (value.includes("bess") || value.includes("speicher")) return "good";
  if (value.includes("wind") || value.includes("pv")) return "neutral";
  return "warn";
}

function buildComponents(
  input: GridCheckInput,
  result: GridCheckResult,
  meta?: VisualizationMeta,
): ProjectComponentChip[] {
  const baseLabels =
    result.projektprofil.component_summary.length > 0
      ? result.projektprofil.component_summary
      : [meta?.erzeugungstyp || ANLAGENTYP_LABELS[input.anlagentyp]];

  const extraLabels = result.speicher_bewertung.relevant ? ["Netzdienlicher Speicherpfad"] : [];

  return uniq([...baseLabels, ...extraLabels]).slice(0, 5).map((label) => ({
    label,
    tone: componentTone(label),
    icon: componentIcon(label),
  }));
}

function buildBadges(
  input: GridCheckInput,
  result: GridCheckResult,
  meta: VisualizationMeta | undefined,
  distanceKm: number | null,
): PlanBadge[] {
  return [
    { label: "Mapbox-Kartenausschnitt", tone: "neutral" },
    { label: SPANNUNG_LABELS[input.spannungsebene], tone: "neutral" },
    {
      label: TOPOLOGIE_LABELS[input.topologie],
      tone: input.topologie === "unbekannt" ? "warn" : "neutral",
    },
    {
      label: distanceKm ? `Korridor ca. ${formatNumber(distanceKm, 1)} km` : "Korridor indikativ",
      tone: distanceKm ? "neutral" : "warn",
    },
    {
      label: `Confidence ${result.daten_confidence}`,
      tone:
        result.daten_confidence === "A" || result.daten_confidence === "B" ? "good" : "warn",
    },
    {
      label: result.n1.n1_klasse ? `N-1 ${result.n1.n1_klasse}` : "N-1 noch offen",
      tone:
        result.n1.n1_klasse === "N1-4"
          ? "good"
          : result.n1.n1_klasse === "N1-3"
            ? "neutral"
            : "warn",
    },
    {
      label: result.n1.dso_daten_vorhanden ? "DSO-Daten verifiziert" : "DSO-Daten offen",
      tone: result.n1.dso_daten_vorhanden ? "good" : "warn",
    },
    ...(meta?.kundentyp
      ? [
          {
            label: KUNDENTYP_LABELS[meta.kundentyp] ?? meta.kundentyp,
            tone: "neutral" as Tone,
          },
        ]
      : []),
  ];
}

function buildRiskNotes(result: GridCheckResult): RiskNote[] {
  const notes: RiskNote[] = [
    {
      title: "N-1 Nachweistiefe",
      body:
        result.n1.stufenbegruendung ||
        result.n1.detail_text ||
        "N-1-Stufe wurde im Backend nicht naeher begruendet.",
      tone:
        result.n1.bewertung === "GRUEN"
          ? "good"
          : result.n1.bewertung === "GELB"
            ? "warn"
            : result.n1.bewertung === "ROT"
              ? "critical"
              : "neutral",
      icon: Gauge,
    },
    {
      title: "Trasse / Umwelt",
      body:
        result.route_environment.summary ||
        result.route_environment.drivers[0] ||
        "Noch keine vertieften Trassenhinweise im Ergebnis enthalten.",
      tone: toneFromRouteLevel(result.route_environment.risk_level),
      icon: Route,
    },
    {
      title: "Stakeholder-Fokus",
      body:
        result.stakeholder_bewertung.recommended_focus ||
        result.stakeholder_bewertung.konflikt_summary ||
        "Abstimmung mit VNB und Projektteam frueh einplanen.",
      tone:
        result.stakeholder_bewertung.konflikt_level === "hoch"
          ? "critical"
          : result.stakeholder_bewertung.konflikt_level === "mittel"
            ? "warn"
            : "good",
      icon: Workflow,
    },
  ];

  if (result.speicher_bewertung.relevant) {
    notes.push({
      title: "Speicherpfad",
      body:
        result.speicher_bewertung.summary ||
        result.speicher_bewertung.disclaimer ||
        "Speicher kann netzdienliche Betriebsweisen unterstuetzen.",
      tone: toneFromScore(result.speicher_bewertung.grid_support_score),
      icon: BatteryCharging,
    });
  }

  return notes.slice(0, 4);
}

function buildAssumptions(
  input: GridCheckInput,
  result: GridCheckResult,
  distanceKm: number | null,
): string[] {
  const hasCoordinates =
    typeof input.project_location?.latitude === "number" &&
    Number.isFinite(input.project_location.latitude) &&
    typeof input.project_location?.longitude === "number" &&
    Number.isFinite(input.project_location.longitude);
  const hasAddressHint = Boolean(input.project_location?.address_hint?.trim());

  return uniq([
    ...result.transparenz.assumptions,
    ...result.n1.detail_annahmen,
    distanceKm
      ? `Der Kartenkorridor wurde mit ca. ${formatNumber(distanceKm, 1)} km aus Eingabe und Backend-Werten aufgespannt.`
      : "Es liegt keine belastbare Trassenlaenge vor; die Netzgeometrie bleibt indikativ.",
    hasCoordinates
      ? "Der Projektstandort basiert auf explizit hinterlegten Koordinaten."
      : hasAddressHint
        ? "Der Projektstandort basiert auf einem Standorthinweis mit Mapbox-Geocoding."
        : input.ort?.trim()
          ? "Der Projektstandort basiert auf Ort- und PLZ-Geocoding."
          : "Der Projektstandort basiert nur auf PLZ-Geocoding und bleibt entsprechend grob.",
    input.topologie === "unbekannt"
      ? "Die Netz-Topologie ist noch nicht verifiziert."
      : `Die visuelle Struktur folgt der Topologieannahme ${TOPOLOGIE_LABELS[input.topologie]}.`,
    "NAP-, Stations- und NVP-Positionen werden fuer die UX aus Distanz-, Topologie- und Belastungsdaten heuristisch entlang des Korridors abgeleitet.",
  ]).slice(0, 5);
}

function buildDisclaimers(result: GridCheckResult): string[] {
  return uniq([
    ...result.transparenz.disclaimers,
    ...result.transparenz.confidence_notes,
    "Der Projektmarker zeigt die beste verfuegbare reale Lagequelle; Netzobjekte und Leitungsverlaeufe bleiben bewusst indikativ.",
    "Vorlaeufige technische Einordnung, keine Netzanschlusszusage und keine bestaetigte freie Kapazitaet.",
    "Finale Trasse, NVP, Schutz- und Schaltkonzept muessen mit dem zustaendigen Netzbetreiber abgestimmt werden.",
  ]).slice(0, 5);
}

export default function NetzplanVisualization({
  input,
  result,
  meta,
}: NetzplanVisualizationProps) {
  const distanceKm = pickPositive(input.entfernung_km, result.nvp_entfernung_km);
  const resultTone = toneFromMachbarkeit(result.machbarkeit_stufe);
  const projectTitle =
    meta?.projektname?.trim() || meta?.erzeugungstyp?.trim() || ANLAGENTYP_LABELS[input.anlagentyp];
  const locationLabel = uniq([
    input.project_location?.address_hint,
    meta?.ort,
    input.ort,
    input.plz,
  ]).join(" - ");
  const components = buildComponents(input, result, meta);
  const badges = buildBadges(input, result, meta, distanceKm);
  const riskNotes = buildRiskNotes(result);
  const assumptions = buildAssumptions(input, result, distanceKm);
  const disclaimers = buildDisclaimers(result);
  const nextSteps = uniq([...result.empfehlungen, ...result.route_environment.mitigation]).slice(0, 4);

  const scoreMetrics: ScoreMetric[] = [
    {
      label: "Kapazitaet",
      value: result.teil_scores.kapazitaet,
      tone: toneFromScore(result.teil_scores.kapazitaet),
    },
    {
      label: "Spannung",
      value: result.teil_scores.spannung,
      tone: toneFromScore(result.teil_scores.spannung),
    },
    {
      label: "Kurzschluss",
      value: result.teil_scores.kurzschluss,
      tone: toneFromScore(result.teil_scores.kurzschluss),
    },
    {
      label: "N-1",
      value: result.teil_scores.n1,
      tone: toneFromScore(result.teil_scores.n1),
    },
  ];

  const rawMetrics: RawMetric[] = [
    {
      label: "|dU|",
      value: `${formatNumber(Math.abs(result.delta_u_pct), 2)} %`,
      detail: result.delta_u_isRise ? "Spannungsanhebung" : "Spannungsfall",
      tone: toneFromScore(result.teil_scores.spannung),
    },
    {
      label: "Trafo",
      value: `${formatNumber(result.trafo_auslastung_pct, 1)} %`,
      detail: "Auslastung",
      tone: toneFromUtilization(result.trafo_auslastung_pct),
    },
    {
      label: "Leitung",
      value: `${formatNumber(result.leitung_auslastung_pct, 1)} %`,
      detail: "Thermische Reserve",
      tone: toneFromUtilization(result.leitung_auslastung_pct),
    },
    {
      label: "Ik max",
      value: `${formatNumber(result.kurzschluss.ik_max_kA, 1)} kA`,
      detail: "Kurzschluss am Screeningpunkt",
      tone: toneFromScore(result.teil_scores.kurzschluss),
    },
  ];

  return (
    <section className="rounded-[28px] border border-border/70 bg-[linear-gradient(180deg,rgba(10,35,35,0.96)_0%,rgba(6,26,26,0.98)_100%)] p-6 shadow-[0_18px_64px_rgba(0,0,0,0.22)]">
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-brand-cyan/25 bg-brand-cyan/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-brand-cyan">
              <Network className="h-3.5 w-3.5" />
              Netzplanvisualisierung
            </div>
            <div>
              <h3 className="text-2xl font-semibold text-white">Netz- und Anschlussplan</h3>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-text-muted">
                Mapbox-basierte Ansicht fuer den Anschlusskorridor zwischen{" "}
                <span className="text-white">{result.nvp_bezeichnung}</span> und{" "}
                <span className="text-white">{projectTitle}</span>.
                {locationLabel ? ` Standortbezug: ${locationLabel}.` : ""}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {badges.map((badge) => (
                <span
                  key={badge.label}
                  className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${TONE_STYLES[badge.tone].badge}`}
                >
                  {badge.label}
                </span>
              ))}
            </div>
          </div>

          <div className={`rounded-2xl border px-4 py-3 ${TONE_STYLES[resultTone].panel}`}>
            <div className="text-xs uppercase tracking-[0.2em] text-text-dim">Machbarkeit</div>
            <div className={`mt-1 text-2xl font-semibold ${TONE_STYLES[resultTone].text}`}>
              {MACHBARKEIT_LABELS[result.machbarkeit_stufe]}
            </div>
            <div className="mt-1 text-sm text-text-muted">
              Score {formatNumber(result.score, 0)}/100 · {RICHTUNG_LABELS[input.richtung]}
            </div>
            <div className="mt-2 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-text-muted">
              <Info className="h-3.5 w-3.5" />
              PLZ geocodiert, Netzlayer heuristisch
            </div>
          </div>
        </div>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.7fr)_360px]">
          <NetzplanMapPanel
            input={input}
            result={result}
            projectTitle={projectTitle}
            ortHint={meta?.ort ?? input.ort}
          />

          <div className="space-y-4">
            <div className="rounded-[24px] border border-border/60 bg-bg-card/70 p-4">
              <div className="mb-4 flex items-center gap-2">
                <Gauge className="h-4 w-4 text-brand-cyan" />
                <h4 className="text-sm font-semibold text-white">Technische Schwerpunkte</h4>
              </div>
              <div className="space-y-3">
                {scoreMetrics.map((metric) => (
                  <div key={metric.label}>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="text-text-muted">{metric.label}</span>
                      <span className={TONE_STYLES[metric.tone].text}>
                        {formatNumber(metric.value, 0)} %
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-white/5">
                      <div
                        className="h-2 rounded-full"
                        style={{
                          width: `${clampPercent(metric.value)}%`,
                          backgroundColor: TONE_STYLES[metric.tone].line,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3">
                {rawMetrics.map((metric) => (
                  <div key={metric.label} className={`rounded-2xl border px-3 py-3 ${TONE_STYLES[metric.tone].panel}`}>
                    <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">
                      {metric.label}
                    </div>
                    <div className={`mt-1 text-lg font-semibold ${TONE_STYLES[metric.tone].text}`}>
                      {metric.value}
                    </div>
                    <div className="mt-1 text-xs text-text-muted">{metric.detail}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[24px] border border-border/60 bg-bg-card/70 p-4">
              <div className="mb-4 flex items-center gap-2">
                <Factory className="h-4 w-4 text-brand-orange" />
                <h4 className="text-sm font-semibold text-white">Projektcluster</h4>
              </div>
              <div className="flex flex-wrap gap-2">
                {components.map((component) => {
                  const Icon = component.icon;
                  return (
                    <span
                      key={component.label}
                      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${TONE_STYLES[component.tone].badge}`}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      {component.label}
                    </span>
                  );
                })}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-text-dim">Export</div>
                  <div className="mt-1 text-white">
                    {formatNumber(result.projektprofil.max_export_kw, 0)} kW
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-text-dim">Import</div>
                  <div className="mt-1 text-white">
                    {formatNumber(result.projektprofil.max_import_kw, 0)} kW
                  </div>
                </div>
              </div>
              {result.projektprofil.summary && (
                <p className="mt-4 text-sm leading-6 text-text-muted">{result.projektprofil.summary}</p>
              )}
            </div>

            <div className="rounded-[24px] border border-border/60 bg-bg-card/70 p-4">
              <div className="mb-4 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-300" />
                <h4 className="text-sm font-semibold text-white">Engpass- und Risiko-Hinweise</h4>
              </div>
              <div className="space-y-3">
                {riskNotes.map((note) => {
                  const Icon = note.icon;
                  return (
                    <div key={note.title} className={`rounded-2xl border px-3 py-3 ${TONE_STYLES[note.tone].panel}`}>
                      <div className="flex items-start gap-3">
                        <div className={`mt-0.5 rounded-xl p-2 ${TONE_STYLES[note.tone].badge}`}>
                          <Icon className="h-4 w-4" />
                        </div>
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-white">{note.title}</div>
                          <div className="mt-1 text-xs leading-5 text-text-muted">{note.body}</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
          <div className="rounded-[24px] border border-border/60 bg-bg-card/70 p-4">
            <div className="mb-4 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-brand-cyan" />
              <h4 className="text-sm font-semibold text-white">Legende und naechste Schritte</h4>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {[
                {
                  label: "Stabil / belastbar",
                  description: "Backend-Scores und Lastindikatoren sprechen fuer einen tragfaehigen Pfad.",
                  tone: "good" as Tone,
                },
                {
                  label: "Auflagen / Monitoring",
                  description: "Randbedingungen oder Zusatzdaten sollten vor Anschlussentscheidung geprueft werden.",
                  tone: "warn" as Tone,
                },
                {
                  label: "Kritischer Engpass",
                  description: "Orange und Rot markieren Belastungsspitzen oder hohen Ausbaubedarf im Kartenpfad.",
                  tone: "critical" as Tone,
                },
                {
                  label: "Georeferenzierte Basis",
                  description: "Der Kartenausschnitt ist echt; Netzobjekte werden bewusst als heuristische Layer kenntlich gemacht.",
                  tone: "neutral" as Tone,
                },
              ].map((item) => (
                <div key={item.label} className={`rounded-2xl border px-4 py-3 ${TONE_STYLES[item.tone].panel}`}>
                  <div className="flex items-center gap-2 text-sm font-medium text-white">
                    <span className={`h-2.5 w-2.5 rounded-full ${TONE_STYLES[item.tone].dot}`} />
                    {item.label}
                  </div>
                  <p className="mt-2 text-xs leading-5 text-text-muted">{item.description}</p>
                </div>
              ))}
            </div>

            {nextSteps.length > 0 && (
              <div className="mt-5 rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                <div className="text-xs uppercase tracking-[0.18em] text-text-dim">
                  Empfohlene naechste Schritte
                </div>
                <ul className="mt-3 space-y-2 text-sm text-text-muted">
                  {nextSteps.map((step) => (
                    <li key={step} className="flex gap-2">
                      <span className="text-brand-orange">•</span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="rounded-[24px] border border-border/60 bg-bg-card/70 p-4">
            <div className="mb-4 flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-brand-orange" />
              <h4 className="text-sm font-semibold text-white">Annahmen und Disclaimer</h4>
            </div>

            <div className="space-y-4">
              <div>
                <div className="text-xs uppercase tracking-[0.18em] text-text-dim">Annahmen</div>
                <ul className="mt-3 space-y-2 text-sm text-text-muted">
                  {assumptions.map((item) => (
                    <li key={item} className="flex gap-2">
                      <span className="text-brand-cyan">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-2xl border border-brand-orange/20 bg-brand-orange/10 px-4 py-4">
                <div className="text-xs uppercase tracking-[0.18em] text-brand-orange">
                  Wichtige Klarstellung
                </div>
                <ul className="mt-3 space-y-2 text-sm text-text-muted">
                  {disclaimers.map((item) => (
                    <li key={item} className="flex gap-2">
                      <span className="text-brand-orange">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
