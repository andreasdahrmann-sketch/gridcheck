"use client";

import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  Factory,
  Gauge,
  GitBranch,
  ShieldAlert,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import type { GridCheckResult } from "@/types";

type Tone = "good" | "warn" | "critical" | "neutral";

type MetricCard = {
  label: string;
  value: string;
  detail: string;
  tone: Tone;
};

type ComponentCard = {
  title: string;
  icon: LucideIcon;
  tone: Tone;
  status: GridCheckResult["n1_analyse"]["n1_topologie"]["bewertung"];
  summary: string;
  metrics: Array<{ label: string; value: string }>;
};

const TONE_STYLES: Record<
  Tone,
  {
    badge: string;
    panel: string;
    icon: string;
    text: string;
  }
> = {
  good: {
    badge: "border-emerald-400/30 bg-emerald-500/10 text-emerald-100",
    panel: "border-emerald-400/20 bg-emerald-500/10",
    icon: "text-emerald-300",
    text: "text-emerald-200",
  },
  warn: {
    badge: "border-amber-400/30 bg-amber-500/10 text-amber-100",
    panel: "border-amber-400/20 bg-amber-500/10",
    icon: "text-amber-200",
    text: "text-amber-100",
  },
  critical: {
    badge: "border-rose-400/30 bg-rose-500/10 text-rose-100",
    panel: "border-rose-400/20 bg-rose-500/10",
    icon: "text-rose-200",
    text: "text-rose-100",
  },
  neutral: {
    badge: "border-brand-cyan/25 bg-brand-cyan/10 text-brand-cyan",
    panel: "border-brand-cyan/20 bg-brand-cyan/10",
    icon: "text-brand-cyan",
    text: "text-brand-cyan",
  },
};

function formatNumber(value: number, digits = 0): string {
  return new Intl.NumberFormat("de-DE", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

function toneFromBewertung(
  value: GridCheckResult["n1_analyse"]["n1_topologie"]["bewertung"] | GridCheckResult["n1"]["bewertung"],
): Tone {
  if (value === "GRUEN") return "good";
  if (value === "GELB") return "warn";
  if (value === "ROT") return "critical";
  return "neutral";
}

function toneFromSecure(value: GridCheckResult["n1"]["n1_sicher"]): Tone {
  if (value === true) return "good";
  if (value === false) return "critical";
  return "warn";
}

function secureLabel(value: GridCheckResult["n1"]["n1_sicher"]): string {
  if (value === true) return "screeningseitig plausibel";
  if (value === false) return "kritischer N-1-Hinweis";
  return "nur vorlaeufig beurteilbar";
}

function statusLabel(
  value: GridCheckResult["n1_analyse"]["n1_topologie"]["bewertung"] | GridCheckResult["n1"]["bewertung"],
): string {
  if (value === "GRUEN") return "Gruen";
  if (value === "GELB") return "Gelb";
  if (value === "ROT") return "Rot";
  return "Nicht geprueft";
}

function firstText(...values: Array<string | undefined | null>): string {
  for (const value of values) {
    if (typeof value === "string" && value.trim().length > 0) return value;
  }
  return "Noch keine belastbare Einordnung vorhanden.";
}

function compactList(values: string[]): string[] {
  return Array.from(new Set(values.map((item) => item.trim()).filter((item) => item.length > 0)));
}

export default function N1AssessmentPanel({ result }: { result: GridCheckResult }) {
  const summaryTone = toneFromSecure(result.n1.n1_sicher);
  const analysis = result.n1_analyse;
  const assumptions = compactList([
    ...result.n1.detail_annahmen,
    ...analysis.annahmen.map((item) => item.begruendung ?? ""),
  ]);

  const summaryCards: MetricCard[] = [
    {
      label: "Nachweistiefe",
      value: result.n1.n1_klasse ?? "N1-0",
      detail: firstText(result.n1.stufenbegruendung, analysis.gesamt.stufenbegruendung),
      tone: toneFromBewertung(result.n1.bewertung),
    },
    {
      label: "Gesamtstatus",
      value: secureLabel(result.n1.n1_sicher),
      detail: result.n1.dso_daten_vorhanden
        ? "Mit verifizierter Datengrundlage im Screening."
        : "Ohne verifizierte Netzbetreiberdaten konservativ bewertet.",
      tone: summaryTone,
    },
    {
      label: "Engpass",
      value:
        result.n1.engpass_komponente && result.n1.engpass_komponente !== "keine"
          ? result.n1.engpass_komponente
          : "kein dominanter Engpass",
      detail: firstText(result.n1.detail_text, result.n1.topologie_text),
      tone:
        result.n1.engpass_komponente && result.n1.engpass_komponente !== "keine"
          ? toneFromBewertung(result.n1.bewertung)
          : "good",
    },
    {
      label: "Nachweise",
      value: `${result.n1.nachweise_vorhanden.length} vorhanden / ${result.n1.nachweise_fehlend.length} offen`,
      detail: result.n1.n1_konfidenz
        ? `Konfidenz ${formatNumber(result.n1.n1_konfidenz * 100, 0)} %`
        : "Konfidenz im Backend nicht gesondert ausgewiesen.",
      tone:
        result.n1.nachweise_fehlend.length > 0
          ? result.n1.nachweise_vorhanden.length > 0
            ? "warn"
            : "critical"
          : "good",
    },
  ];

  const componentCards: ComponentCard[] = [
    {
      title: "Topologie / Umschaltung",
      icon: Workflow,
      tone: toneFromBewertung(analysis.n1_topologie.bewertung),
      status: analysis.n1_topologie.bewertung,
      summary: firstText(
        analysis.n1_topologie.begruendung_klartext,
        result.n1.topologie_text,
      ),
      metrics: [
        { label: "Topologie", value: result.n1.topologie || "nicht benannt" },
      ],
    },
    {
      title: "Abgangsreserve",
      icon: GitBranch,
      tone: toneFromBewertung(analysis.n1_abgang.bewertung),
      status: analysis.n1_abgang.bewertung,
      summary: firstText(analysis.n1_abgang.begruendung_klartext),
      metrics: [
        {
          label: "Primaer",
          value: analysis.n1_abgang.primaer_abgang_label || "offen",
        },
        {
          label: "Reserve",
          value:
            typeof analysis.n1_abgang.beste_reserve_a === "number"
              ? `${formatNumber(analysis.n1_abgang.beste_reserve_a, 0)} A`
              : "nicht quantifiziert",
        },
        {
          label: "Reservefaktor",
          value:
            typeof analysis.n1_abgang.reserve_ratio === "number"
              ? formatNumber(analysis.n1_abgang.reserve_ratio, 2)
              : "offen",
        },
      ],
    },
    {
      title: "Leitung im N-1-Fall",
      icon: Gauge,
      tone: toneFromBewertung(analysis.n1_leitung.bewertung),
      status: analysis.n1_leitung.bewertung,
      summary: firstText(analysis.n1_leitung.begruendung_klartext, result.n1.leitung_text),
      metrics: [
        {
          label: "Auslastung",
          value:
            typeof analysis.n1_leitung.auslastung_n1_prozent === "number"
              ? `${formatNumber(analysis.n1_leitung.auslastung_n1_prozent, 1)} %`
              : "nicht berechnet",
        },
        {
          label: "I N-1",
          value:
            typeof analysis.n1_leitung.i_n1_a === "number"
              ? `${formatNumber(analysis.n1_leitung.i_n1_a, 0)} A`
              : "offen",
        },
        {
          label: "I max",
          value:
            typeof analysis.n1_leitung.iz_a === "number"
              ? `${formatNumber(analysis.n1_leitung.iz_a, 0)} A`
              : "offen",
        },
      ],
    },
    {
      title: "Traforeserve",
      icon: Factory,
      tone: toneFromBewertung(analysis.n1_trafo.bewertung),
      status: analysis.n1_trafo.bewertung,
      summary: firstText(analysis.n1_trafo.begruendung_klartext),
      metrics: [
        {
          label: "Auslastung N-1",
          value:
            typeof analysis.n1_trafo.auslastung_n1_prozent === "number"
              ? `${formatNumber(analysis.n1_trafo.auslastung_n1_prozent, 1)} %`
              : "nicht berechnet",
        },
        {
          label: "Engpass-Trafo",
          value:
            typeof analysis.n1_trafo.engpass_trafo_idx === "number" && analysis.n1_trafo.engpass_trafo_idx >= 0
              ? `T${analysis.n1_trafo.engpass_trafo_idx + 1}`
              : "offen",
        },
      ],
    },
    {
      title: "Spannungshaltung",
      icon: ShieldCheck,
      tone: toneFromBewertung(analysis.n1_spannung.bewertung),
      status: analysis.n1_spannung.bewertung,
      summary: firstText(analysis.n1_spannung.begruendung_klartext),
      metrics: [
        {
          label: "Delta U N-1",
          value:
            typeof analysis.n1_spannung.delta_u_n1_prozent === "number"
              ? `${formatNumber(analysis.n1_spannung.delta_u_n1_prozent, 2)} %`
              : "nicht berechnet",
        },
        {
          label: "Grenze",
          value:
            typeof analysis.n1_spannung.grenze_prozent === "number"
              ? `${formatNumber(analysis.n1_spannung.grenze_prozent, 1)} %`
              : "offen",
        },
      ],
    },
  ];

  return (
    <section className="rounded-[28px] border border-border/70 bg-[linear-gradient(180deg,rgba(10,35,35,0.96)_0%,rgba(6,26,26,0.98)_100%)] p-4 shadow-[0_18px_52px_rgba(0,0,0,0.22)] sm:p-5">
      <div className="space-y-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-brand-cyan">
              <ShieldCheck className="h-3.5 w-3.5" />
              N-1 Bewertung
            </div>
            <div>
              <h3 className="text-xl font-semibold text-white sm:text-2xl">Nachweistiefe, Engpass und offene Punkte</h3>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-text-muted">
                Die N-1-Darstellung trennt bewusst zwischen Nachweistiefe, belastbaren Nachweisen,
                offenen Annahmen und dem fachlich dominanten Engpass.
              </p>
            </div>
          </div>

          <div className={`rounded-2xl border px-4 py-3 ${TONE_STYLES[summaryTone].panel}`}>
            <div className="text-xs uppercase tracking-[0.18em] text-text-dim">Kurzfazit</div>
            <div className={`mt-1 text-lg font-semibold ${TONE_STYLES[summaryTone].text}`}>
              {result.n1.n1_klasse ?? "N1-0"} · {secureLabel(result.n1.n1_sicher)}
            </div>
            <div className="mt-1 text-sm text-text-muted">
              {result.n1.dso_daten_vorhanden ? "Verifizierte Netzbetreiberdaten vorhanden." : "Vorlaeufiges Screening ohne verifizierte DSO-Daten."}
            </div>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {summaryCards.map((card) => (
            <div key={card.label} className={`rounded-2xl border p-4 ${TONE_STYLES[card.tone].panel}`}>
              <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">{card.label}</div>
              <div className={`mt-2 text-base font-semibold sm:text-lg ${TONE_STYLES[card.tone].text}`}>
                {card.value}
              </div>
              <p className="mt-2 text-xs leading-5 text-text-muted">{card.detail}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
          <div className="rounded-[24px] border border-white/10 bg-white/5 p-4">
            <div className="mb-3 flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-brand-orange" />
              <h4 className="text-sm font-semibold text-white">Stufenkommunikation</h4>
            </div>
            <p className="text-sm leading-6 text-white/90">
              {firstText(result.n1.stufenbegruendung, analysis.gesamt.stufenbegruendung)}
            </p>
            <p className="mt-3 text-sm leading-6 text-text-muted">
              {firstText(result.n1.detail_text, result.n1.topologie_text)}
            </p>
          </div>

          <div className="rounded-[24px] border border-brand-orange/20 bg-brand-orange/10 p-4">
            <div className="mb-3 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-brand-orange" />
              <h4 className="text-sm font-semibold text-white">Offene Nachweise</h4>
            </div>
            {result.n1.nachweise_fehlend.length > 0 ? (
              <ul className="space-y-2 text-sm text-text-muted">
                {result.n1.nachweise_fehlend.map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="text-brand-orange">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-text-muted">Der Backend-Run markiert aktuell keine offenen N-1-Nachweise.</p>
            )}
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {componentCards.map((card) => {
            const Icon = card.icon;
            return (
              <div key={card.title} className="rounded-[24px] border border-white/10 bg-white/5 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className={`rounded-2xl border p-2 ${TONE_STYLES[card.tone].badge}`}>
                      <Icon className={`h-4 w-4 ${TONE_STYLES[card.tone].icon}`} />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">{card.title}</p>
                      <span className={`mt-2 inline-flex rounded-full border px-2.5 py-1 text-[11px] font-medium ${TONE_STYLES[card.tone].badge}`}>
                        {statusLabel(card.status)}
                      </span>
                    </div>
                  </div>
                </div>

                <p className="mt-3 text-sm leading-6 text-text-muted">{card.summary}</p>

                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {card.metrics.map((metric) => (
                    <div key={`${card.title}-${metric.label}`} className="rounded-2xl border border-white/10 bg-black/10 px-3 py-3">
                      <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">{metric.label}</div>
                      <div className="mt-1 text-sm font-semibold text-white">{metric.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-[24px] border border-white/10 bg-white/5 p-4">
            <div className="mb-3 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-brand-cyan" />
              <h4 className="text-sm font-semibold text-white">Vorhandene Nachweise</h4>
            </div>
            <div className="flex flex-wrap gap-2">
              {result.n1.nachweise_vorhanden.length > 0 ? (
                result.n1.nachweise_vorhanden.map((item) => (
                  <span key={item} className="inline-flex rounded-full border border-brand-cyan/25 bg-brand-cyan/10 px-3 py-1.5 text-xs text-brand-cyan">
                    {item}
                  </span>
                ))
              ) : (
                <span className="inline-flex rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-text-muted">
                  Noch keine belastbaren Nachweise im Ergebnis.
                </span>
              )}
            </div>
          </div>

          <div className="rounded-[24px] border border-white/10 bg-white/5 p-4">
            <div className="mb-3 flex items-center gap-2">
              <CircleDashed className="h-4 w-4 text-brand-orange" />
              <h4 className="text-sm font-semibold text-white">Annahmen und Grenzen</h4>
            </div>
            <ul className="space-y-2 text-sm text-text-muted">
              {(assumptions.length > 0 ? assumptions : ["Keine gesonderten N-1-Annahmen ausgewiesen."]).map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="text-brand-orange">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {result.n1.detail_empfehlungen.length > 0 ? (
          <div className="rounded-[24px] border border-white/10 bg-white/5 p-4">
            <div className="mb-3 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-brand-cyan" />
              <h4 className="text-sm font-semibold text-white">Gezielte N-1-Folgeschritte</h4>
            </div>
            <ul className="grid gap-2 text-sm text-text-muted sm:grid-cols-2">
              {result.n1.detail_empfehlungen.map((item) => (
                <li key={item} className="rounded-2xl border border-white/10 bg-black/10 px-3 py-3">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </section>
  );
}
