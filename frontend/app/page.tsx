"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, Sparkles } from "lucide-react";
import { Header } from "@/components/Header";
import NetzbetreiberDashboard from "@/components/dashboard/NetzbetreiberDashboard";
import { readUserPreferences } from "@/lib/user-preferences";

const GridCheckForm = dynamic(() => import("@/components/GridCheckForm"), {
  loading: () => <div className="text-sm text-text-muted">Lade Check-Modul...</div>,
});

const ROLE_CARDS = [
  {
    title: "Projektierer",
    status: "Aktiv",
    href: "/projektierer",
    description: "Aktiver Pfad fuer Vorqualifizierung, Variantenvergleich, Kosten-/Trassenklaerung und VNB-/Invest-Vorbereitung.",
    cta: "Projektierer-Modul oeffnen",
    active: true,
  },
  {
    title: "VNB",
    status: "Aktiv",
    href: "/vnb",
    description: "Aktiver Pfad fuer strukturierte Anfragepruefung, technische Vorpruefung, Auflagen und Audit-/Prozesssicht.",
    cta: "VNB-Modul oeffnen",
    active: true,
  },
  {
    title: "Invest",
    status: "Aktiv",
    href: "/invest",
    description: "Aktiver Pfad fuer Standortbewertung, Risikoanalyse, Kostenbandbreite und Due-Diligence-orientierte Outputs.",
    cta: "Invest-Modul oeffnen",
    active: true,
  },
];

const MVP_POINTS = [
  "Die MVP-Rollenpfade /projektierer, /vnb und /invest sind aktiv und fuehren in differenzierte Nutzerfluesse.",
  "3 Checks kostenlos pro Nutzer, danach serverseitige Paywall.",
  "Pay-per-Use-Pakete und Pro-Lizenz sind unter Tarife & Preise dokumentiert.",
  "Invest blendet tiefe Netzdaten bewusst aus; VNB und Projektierer behalten technische Tiefensicht nach Rollenlogik.",
  "Professional ist Servicepfad, Express ein Zeit-Add-on und VNB Pilot kein Self-Serve-Angebot.",
];

export default function Home() {
  const [tab, setTab] = useState<"check" | "dashboard">("check");

  useEffect(() => {
    const { defaultLandingTab } = readUserPreferences();
    setTab(defaultLandingTab);
  }, []);

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />

      <section className="border-b border-border/70 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.16),transparent_30%),radial-gradient(circle_at_top_right,rgba(249,115,22,0.12),transparent_24%)]">
        <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
          <div className="grid gap-8 xl:grid-cols-[minmax(0,1.2fr)_minmax(300px,0.75fr)] xl:items-start">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-brand-cyan">
                <Sparkles className="h-4 w-4" />
                Fruehe Netzanschluss-Klarheit
              </div>
              <h1 className="mt-5 max-w-4xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                Netzanschluss-Klarheit vor dem Antrag.
              </h1>
              <p className="mt-4 max-w-3xl text-lg leading-8 text-text-muted">
                GridCheck positioniert sich nicht als reine Software zur Netzanschlusspruefung, sondern als fruehe
                Klarheit vor Antrag, Detailplanung und Kapitalbindung.
              </p>
              <p className="mt-4 max-w-3xl text-base leading-7 text-white/85">
                Wir zeigen nicht nur, ob ein Anschluss kritisch ist, sondern unter welchen Bedingungen er strategisch
                besser darstellbar wird.
              </p>
              <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                <Link
                  href="/projektierer"
                  className="inline-flex items-center justify-center rounded-2xl bg-brand-orange px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-orangeHover"
                >
                  Projektierer-Modul oeffnen
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
                <Link
                  href="/preise"
                  className="inline-flex items-center justify-center rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  Tarife & Preise
                </Link>
                <Link
                  href="/contact?intent=professional"
                  className="inline-flex items-center justify-center rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  Professional / Pilot anfragen
                </Link>
              </div>
            </div>

            <aside className="rounded-[28px] border border-white/10 bg-white/5 p-5 shadow-[0_20px_60px_rgba(0,0,0,0.24)]">
              <p className="text-xs font-medium uppercase tracking-[0.22em] text-brand-cyan">Schnellstart</p>
              <p className="mt-3 text-sm leading-6 text-text-muted">
                Starten Sie mit dem Netzanschluss-Check oder waehlen Sie den passenden Rollenpfad. Tarife und
                Paketvergleich finden Sie separat unter Tarife & Preise.
              </p>
              <Link
                href="/preise"
                className="mt-4 inline-flex w-full items-center justify-center rounded-2xl border border-brand-cyan/25 bg-brand-cyan/10 px-4 py-3 text-sm font-semibold text-brand-cyan transition hover:bg-brand-cyan/15"
              >
                Tarife vergleichen
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
              <Link
                href="/settings"
                className="mt-3 inline-flex w-full items-center justify-center rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/5"
              >
                Konto & Upgrade-Pfade
              </Link>
            </aside>
          </div>

          <div className="mt-8 grid gap-4 lg:grid-cols-3 xl:grid-cols-5">
            {MVP_POINTS.map((item) => (
              <div key={item} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4 text-sm leading-6 text-text-muted xl:col-span-1">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-brand-cyan" />
                  <span>{item}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8 grid gap-4 lg:grid-cols-3">
            {ROLE_CARDS.map((item) => (
              <Link
                key={item.title}
                href={item.href}
                className={`rounded-[24px] border p-5 transition ${
                  item.active
                    ? "border-brand-cyan/30 bg-brand-cyan/10 hover:bg-brand-cyan/15"
                    : "border-white/10 bg-white/5 hover:bg-white/10"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-lg font-semibold text-white">{item.title}</p>
                  <span className="inline-flex items-center gap-1 rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-brand-cyan">
                    {item.status}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-text-muted">{item.description}</p>
                <div className="mt-4 inline-flex items-center text-sm font-semibold text-white">
                  {item.cta}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <div className="sticky top-16 z-30 border-b border-border bg-bg/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.22em] text-brand-cyan">Arbeitsbereiche</p>
            <p className="mt-1 text-sm text-text-muted">
              Wechseln Sie zwischen Vorqualifizierung und operativer Antragsansicht.
            </p>
          </div>
          <div className="flex gap-2 rounded-2xl border border-white/10 bg-white/5 p-1.5">
            <button
              onClick={() => setTab("check")}
              className={`flex-1 rounded-xl px-4 py-2.5 text-sm font-medium transition-all sm:flex-none ${
                tab === "check"
                  ? "bg-brand-orange text-white shadow-lg shadow-brand-orange/25"
                  : "text-text-muted hover:bg-bg-elev hover:text-white"
              }`}
            >
              Netzanschluss-Check
            </button>
            <button
              onClick={() => setTab("dashboard")}
              className={`flex-1 rounded-xl px-4 py-2.5 text-sm font-medium transition-all sm:flex-none ${
                tab === "dashboard"
                  ? "bg-brand-mint text-[#05201C] shadow-lg shadow-brand-mint/25"
                  : "text-text-muted hover:bg-bg-elev hover:text-white"
              }`}
            >
              Netzbetreiber-Dashboard
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        {tab === "check" && <GridCheckForm />}
        {tab === "dashboard" && <NetzbetreiberDashboard />}
      </div>
    </main>
  );
}
