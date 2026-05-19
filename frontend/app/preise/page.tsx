import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import { Header } from "@/components/Header";
import PricingOverview from "@/components/billing/PricingOverview";
import ProductDecisionGuide from "@/components/billing/ProductDecisionGuide";

export const metadata = {
  title: "Tarife & Preise — GridCheck",
  description: "Uebersicht der GridCheck-Tarife: Free, Basic, Premium, Pro, Professional und VNB Pilot.",
};

export default function PreisePage() {
  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />

      <section className="border-b border-border/70 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.16),transparent_30%),radial-gradient(circle_at_top_right,rgba(249,115,22,0.12),transparent_24%)]">
        <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
          <div className="inline-flex items-center gap-2 rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-brand-cyan">
            <Sparkles className="h-4 w-4" />
            Produkt & Tarife
          </div>
          <h1 className="mt-5 max-w-3xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
            Tarife & Preise auf einen Blick
          </h1>
          <p className="mt-4 max-w-3xl text-lg leading-8 text-text-muted">
            Vergleichen Sie Self-Serve-Pakete, Lizenzmodelle und Servicepfade. Scope, Checkout und naechster Schritt
            bleiben bewusst getrennt – ohne versteckte Upgrades.
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/settings"
              className="inline-flex items-center justify-center rounded-2xl bg-brand-orange px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-orangeHover"
            >
              Konto & Checkout
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link
              href="/projektierer"
              className="inline-flex items-center justify-center rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              Check starten
            </Link>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl space-y-10 px-4 py-10 sm:px-6 sm:py-12">
        <PricingOverview />

        <ProductDecisionGuide
          title="Welches Paket passt wann?"
          description="Die Entscheidungshilfe ergaenzt die Preisuebersicht um typische Einsatzfaelle, Grenzen und den passenden naechsten Schritt."
        />
      </div>
    </main>
  );
}
