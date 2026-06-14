"use client";

import Link from "next/link";
import { useEffect } from "react";

type ErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function RootError({ error, reset }: ErrorProps) {
  useEffect(() => {
    if (typeof window === "undefined") return;

    // TODO(observability): Sentry-Frontend-SDK ist aktuell nicht installiert
    // (siehe frontend/package.json). Wenn @sentry/nextjs zukünftig hinzukommt,
    // greift dieser defensive Aufruf automatisch — ohne neue Dependency hier.
    try {
      const sentry = (window as unknown as {
        Sentry?: { captureException?: (err: unknown, ctx?: unknown) => void };
        __SENTRY__?: unknown;
      }).Sentry;
      if (sentry?.captureException) {
        sentry.captureException(error, {
          tags: { source: "app/error.tsx", digest: error.digest ?? "unknown" },
        });
      }
    } catch {
      // Fehler im Error-Reporter dürfen die Recovery-UI nicht blockieren.
    }

    if (process.env.NODE_ENV !== "production") {
      console.error("[GridCheck:error.tsx]", error);
    }
  }, [error]);

  return (
    <main className="flex min-h-[60vh] flex-1 items-center justify-center px-6 py-16">
      <div
        role="alert"
        aria-live="assertive"
        className="card w-full max-w-xl space-y-6"
      >
        <div className="space-y-2">
          <p className="pill" aria-hidden="true">
            Unerwarteter Fehler
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-text">
            Da ist etwas schiefgelaufen
          </h1>
          <p className="text-sm text-text-muted">
            Die Aktion konnte nicht abgeschlossen werden. Bitte versuchen Sie es erneut.
            Falls der Fehler bestehen bleibt, melden Sie sich bitte beim Support und
            geben Sie die unten stehende Fehler-ID an.
          </p>
        </div>

        <dl className="grid grid-cols-1 gap-1 rounded-xl border border-border bg-bg-soft px-4 py-3 text-xs">
          <div className="flex items-center justify-between gap-3">
            <dt className="font-medium uppercase tracking-wider text-text-dim">
              Fehler-ID
            </dt>
            <dd className="font-mono text-text">
              {error.digest ?? "nicht verfügbar"}
            </dd>
          </div>
        </dl>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <button type="button" onClick={() => reset()} className="btn-primary">
            Erneut versuchen
          </button>
          <Link href="/" className="btn-ghost" prefetch={false}>
            Zur Startseite
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
