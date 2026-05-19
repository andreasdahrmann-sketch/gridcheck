"use client";

import Link from "next/link";
import { ArrowRight, FolderKanban, Search, Sparkles } from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";

const steps = [
  {
    title: "1. Ersten Check starten",
    description:
      "Vorlaeufige Netzanschluss-Diagnose mit transparenten Annahmen — keine verbindliche Netzbetreiberzusage.",
    href: "/check",
    icon: Search,
    cta: "Zum Check",
  },
  {
    title: "2. Projekte anlegen",
    description: "Ergebnisse speichern, vergleichen und fuer Ihr Team dokumentieren.",
    href: "/projects",
    icon: FolderKanban,
    cta: "Zu Projekten",
  },
  {
    title: "3. Tarif & Funktionen",
    description: "Mehr Checks, Reports und erweiterte Auswertungen — Uebersicht der Pakete.",
    href: "/preise",
    icon: Sparkles,
    cta: "Preise ansehen",
  },
];

export default function OnboardingPage() {
  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <h1 className="text-3xl font-semibold tracking-tight">Willkommen bei GridCheck</h1>
        <p className="mt-3 text-text-muted">
          Drei Schritte fuer den Einstieg — Sie koennen jederzeit unterbrechen und spaeter fortsetzen.
        </p>

        <ol className="mt-10 space-y-6">
          {steps.map((step) => (
            <li
              key={step.href}
              className="rounded-[24px] border border-white/10 bg-bg-card/80 p-6 shadow-[0_8px_32px_rgba(0,0,0,0.12)]"
            >
              <div className="flex items-start gap-4">
                <step.icon className="mt-1 h-6 w-6 shrink-0 text-brand-cyan" aria-hidden />
                <div className="flex-1">
                  <h2 className="text-lg font-medium text-white">{step.title}</h2>
                  <p className="mt-2 text-sm text-text-muted">{step.description}</p>
                  <Button asChild className="mt-4 h-10 rounded-xl bg-brand-cyan text-slate-950 hover:bg-brand-cyan/90">
                    <Link href={step.href}>
                      {step.cta}
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              {"</motion>".replace("motion", "div")}
            </li>
          ))}
        </ol>

        <p className="mt-8 text-center text-sm text-text-dim">
          <Link href="/projects" className="text-brand-cyan underline">
            Ueberspringen und zu Projekten
          </Link>
        </p>
      </div>
    </main>
  );
}
