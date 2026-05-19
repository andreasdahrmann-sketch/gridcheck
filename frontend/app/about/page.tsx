import Link from "next/link";
import { Header } from "@/components/Header";
import { SiteFooter } from "@/components/layout/SiteFooter";

export const metadata = {
  title: "Ueber GridCheck",
  description: "Was GridCheck leistet – und was bewusst ausserhalb des Produkts bleibt.",
};

export default function AboutPage() {
  return (
    <div className="flex min-h-screen flex-col bg-bg text-white">
      <Header />
      <main className="mx-auto max-w-3xl flex-1 px-4 py-12 sm:px-6">
        <h1 className="text-3xl font-semibold tracking-tight">Ueber GridCheck</h1>
        <p className="mt-4 text-base leading-7 text-text-muted">
          GridCheck unterstuetzt Projektierer, Investoren und Netzbetreiber bei der{" "}
          <strong className="font-medium text-white">vorlaeufigen</strong> Netzanschluss-Diagnose – mit nachvollziehbaren
          Annahmen, Normbezug und revisionssicherer Dokumentation.
        </p>
        <p className="mt-4 text-sm leading-6 text-text-dim">
          Hinweis: Es handelt sich nicht um eine verbindliche Netzanschlusszusage oder Kapazitaetsgarantie. Entscheidungen
          des zustaendigen Netzbetreibers bleiben massgeblich.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/projektierer"
            className="rounded-xl bg-brand-orange px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-orangeHover"
          >
            Analyse starten
          </Link>
          <Link
            href="/contact"
            className="rounded-xl border border-white/15 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/5"
          >
            Kontakt
          </Link>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
