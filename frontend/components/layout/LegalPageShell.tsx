import type { ReactNode } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";

type LegalPageShellProps = {
  badge: string;
  title: string;
  intro: string;
  children: ReactNode;
};

const sectionClass = "rounded-[28px] border border-white/10 bg-white/5 p-6";
const headingClass = "text-lg font-semibold text-white";
const bodyClass = "mt-3 space-y-3 text-sm leading-6 text-text-muted";

export function LegalPageShell({ badge, title, intro, children }: LegalPageShellProps) {
  return (
    <main className="flex min-h-screen flex-col bg-bg text-white">
      <Header />
      <div className="mx-auto w-full max-w-3xl flex-1 px-4 py-6 sm:px-6 sm:py-10">
        <div className={sectionClass}>
          <div className="inline-flex rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-brand-cyan">
            {badge}
          </div>
          <h1 className="mt-4 text-3xl font-semibold text-white">{title}</h1>
          <p className="mt-3 text-sm leading-6 text-text-muted">{intro}</p>
        </div>
        <div className="mt-6 space-y-6">{children}</div>
        <p className="mt-8 text-xs text-text-dim">
          Weitere Fragen?{" "}
          <Link href="/contact" className="font-medium text-brand-cyan hover:underline">
            Kontakt aufnehmen
          </Link>
        </p>
      </div>
    </main>
  );
}

export function LegalSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={sectionClass}>
      <h2 className={headingClass}>{title}</h2>
      <div className={bodyClass}>{children}</div>
    </section>
  );
}

export function PlaceholderNotice() {
  return (
    <p className="rounded-2xl border border-brand-orange/30 bg-brand-orange/10 px-4 py-3 text-sm leading-6 text-brand-orange">
      [BITTE RECHTLICH PRUEFEN] Platzhalter – vor Live mit echten Firmendaten, AV-Vertraegen und finaler
      Rechtsberatung ersetzen.
    </p>
  );
}
