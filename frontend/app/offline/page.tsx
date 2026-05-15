import Link from "next/link";

export default function OfflinePage() {
  return (
    <main className="flex min-h-[100svh] items-center justify-center bg-bg px-4 py-10 text-white">
      <div className="w-full max-w-xl rounded-[28px] border border-white/10 bg-white/5 p-6 shadow-[0_18px_60px_rgba(0,0,0,0.22)] sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-brand-cyan">Offline</p>
        <h1 className="mt-3 text-3xl font-semibold text-white">GridCheck ist gerade ohne Netz geladen.</h1>
        <p className="mt-4 text-sm leading-7 text-text-muted">
          Die App-Shell bleibt installierbar und oeffnet weiter. Live-API-Aufrufe wie Login, Marker-Upload und
          Projekt-Synchronisation brauchen aber wieder eine aktive Verbindung.
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <Link
            href="/site-markers"
            className="inline-flex items-center justify-center rounded-2xl bg-brand-orange px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-orangeHover"
          >
            Zur Feldaufnahme
          </Link>
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
          >
            Zur Startseite
          </Link>
        </div>
      </div>
    </main>
  );
}
