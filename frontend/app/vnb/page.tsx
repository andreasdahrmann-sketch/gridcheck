"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowRight, CheckCircle2, ClipboardList, ShieldAlert, Sparkles } from "lucide-react";
import { Header } from "@/components/Header";

const GridCheckForm = dynamic(() => import("@/components/GridCheckForm"), {
  loading: () => (
    <div className="rounded-[28px] border border-white/10 bg-white/5 px-5 py-6 text-sm text-text-muted">
      Lade VNB-Modul...
    </div>
  ),
});

export default function VnbPage() {
  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <section className="border-b border-border/70 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.16),transparent_30%),radial-gradient(circle_at_top_right,rgba(249,115,22,0.12),transparent_24%)]">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)] xl:items-start">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-brand-cyan">
                <Sparkles className="h-4 w-4" />
                Aktiver Rollenpfad
              </div>
              <h1 className="mt-5 max-w-4xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                VNB-Modul fuer strukturierte Anfragepruefung und technische Vorpruefung.
              </h1>
              <p className="mt-4 max-w-3xl text-base leading-7 text-text-muted sm:text-lg sm:leading-8">
                Der aktive VNB-Pfad verdichtet Antragskern, technische Vorpruefung, N-1-Nachweistiefe, Prozesssicht,
                technische Auflagen und revisionssichere Auditierbarkeit.
              </p>
              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/projects"
                  className="inline-flex items-center justify-center rounded-2xl bg-brand-orange px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-orangeHover"
                >
                  Zu Projekten nach dem Run
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
                <Link
                  href="/contact?intent=vnb-pilot"
                  className="inline-flex items-center justify-center rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  VNB-Pilot anfragen
                </Link>
              </div>
            </div>

            <div className="rounded-[28px] border border-white/10 bg-white/5 p-5 shadow-[0_20px_60px_rgba(0,0,0,0.24)]">
              <p className="text-xs font-medium uppercase tracking-[0.22em] text-brand-cyan">VNB MVP Scope</p>
              <div className="mt-4 space-y-3">
                {[
                  {
                    title: "Strukturierte Anfragepruefung",
                    description: "Standort, Leistung, N-1-Datengrundlage und Netzbezug werden sichtbar und konsistent verdichtet.",
                    icon: ClipboardList,
                  },
                  {
                    title: "Technische Vorpruefung",
                    description: "N-1-, Engpass-, Spannungs- und Auflagenlogik werden fuer den VNB-Kontext separat sprachlich aufbereitet.",
                    icon: CheckCircle2,
                  },
                ].map((item) => (
                  <div key={item.title} className="rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
                    <div className="flex items-center gap-2 text-white">
                      <item.icon className="h-4 w-4 text-brand-cyan" />
                      <p className="text-sm font-semibold">{item.title}</p>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-text-muted">{item.description}</p>
                  </div>
                ))}
              </div>
              <div className="mt-4 rounded-2xl border border-brand-orange/20 bg-brand-orange/10 px-4 py-4 text-sm leading-6 text-text-muted">
                <p className="flex items-center gap-2 font-medium text-white">
                  <ShieldAlert className="h-4 w-4 text-brand-orange" />
                  Keine Freigabe interner Netzdaten
                </p>
                <p className="mt-2">
                  Der VNB-Pfad bleibt konservativ: keine Fake-Kapazitaet, keine stillschweigende Netzfreigabe, keine
                  Scheinsicherheit ohne verifizierte Datengrundlage.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <GridCheckForm forcedCustomerType="netzbetreiber" />
      </section>
    </main>
  );
}
