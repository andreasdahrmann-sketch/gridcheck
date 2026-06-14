import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Seite nicht gefunden — GridCheck",
  description: "Die angeforderte Seite existiert nicht oder wurde verschoben.",
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <main className="flex min-h-[60vh] flex-1 items-center justify-center px-6 py-16">
      <div className="card w-full max-w-xl space-y-6">
        <div className="space-y-2">
          <p className="pill" aria-hidden="true">
            Fehler 404
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-text">
            Seite nicht gefunden
          </h1>
          <p className="text-sm text-text-muted">
            Die angeforderte Seite existiert nicht oder wurde verschoben. Prüfen Sie bitte
            die URL oder kehren Sie zur Startseite zurück.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Link href="/" className="btn-primary" prefetch={false}>
            Zur Startseite
          </Link>
          <Link href="/contact" className="btn-ghost" prefetch={false}>
            Hilfe & Kontakt
          </Link>
        </div>

        <p className="border-t border-border pt-4 text-xs text-text-dim">
          Hinweis: GridCheck liefert vorläufige Diagnosen. Eine rechtsverbindliche
          Netzanschlussprüfung erfolgt ausschließlich durch den zuständigen Netzbetreiber.
        </p>
      </div>
    </main>
  );
}
