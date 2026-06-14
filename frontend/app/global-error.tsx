"use client";

import { useEffect } from "react";

type GlobalErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    if (typeof window === "undefined") return;

    // TODO(observability): Falls @sentry/nextjs später aktiviert wird, greift
    // dieser defensive Aufruf automatisch. KEIN neuer Dependency-Import hier.
    try {
      const sentry = (window as unknown as {
        Sentry?: { captureException?: (err: unknown, ctx?: unknown) => void };
        __SENTRY__?: unknown;
      }).Sentry;
      if (sentry?.captureException) {
        sentry.captureException(error, {
          tags: { source: "app/global-error.tsx", digest: error.digest ?? "unknown" },
        });
      }
    } catch {
      // Fehler im Error-Reporter dürfen die Recovery-UI nicht blockieren.
    }

    if (process.env.NODE_ENV !== "production") {
      console.error("[GridCheck:global-error.tsx]", error);
    }
  }, [error]);

  // Inline-Styles, weil das Root-Layout (inkl. globals.css/Tailwind) hier
  // möglicherweise gecrasht ist. Diese Seite muss eigenständig rendern.
  const colors = {
    bg: "#061A1A",
    bgCard: "#0F2B2B",
    bgSoft: "#0A2323",
    border: "#214242",
    text: "#E7F3F0",
    textMuted: "#9FC2BA",
    textDim: "#6D938A",
    orange: "#EE7F2D",
    orangeHover: "#FF9448",
  };

  const fontStack = "Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif";

  return (
    <html lang="de">
      <head>
        <title>Schwerwiegender Fehler — GridCheck</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="robots" content="noindex,nofollow" />
      </head>
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          background: colors.bg,
          color: colors.text,
          fontFamily: fontStack,
          WebkitFontSmoothing: "antialiased",
        }}
      >
        <main
          style={{
            display: "flex",
            minHeight: "100vh",
            alignItems: "center",
            justifyContent: "center",
            padding: "4rem 1.5rem",
          }}
        >
          <div
            role="alert"
            aria-live="assertive"
            style={{
              width: "100%",
              maxWidth: "36rem",
              background: colors.bgCard,
              border: `1px solid ${colors.border}`,
              borderRadius: "1.25rem",
              padding: "2rem",
              boxShadow: "0 8px 30px rgba(0,0,0,0.28)",
            }}
          >
            <p
              style={{
                display: "inline-block",
                padding: "0.25rem 0.75rem",
                margin: 0,
                marginBottom: "1rem",
                borderRadius: "9999px",
                background: "rgba(238,127,45,0.14)",
                color: colors.orange,
                border: "1px solid rgba(238,127,45,0.34)",
                fontSize: "0.7rem",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}
            >
              Schwerwiegender Fehler
            </p>
            <h1 style={{ fontSize: "1.75rem", margin: "0 0 0.75rem", fontWeight: 600 }}>
              GridCheck konnte nicht geladen werden
            </h1>
            <p style={{ margin: "0 0 1.25rem", color: colors.textMuted, fontSize: "0.95rem", lineHeight: 1.5 }}>
              Es ist ein unerwarteter Fehler im Anwendungsrahmen aufgetreten. Bitte
              versuchen Sie es erneut. Falls der Fehler bestehen bleibt, melden Sie
              sich beim Support und geben Sie die unten stehende Fehler-ID an.
            </p>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "0.75rem",
                padding: "0.75rem 1rem",
                marginBottom: "1.25rem",
                background: colors.bgSoft,
                border: `1px solid ${colors.border}`,
                borderRadius: "0.75rem",
                fontSize: "0.8rem",
              }}
            >
              <span style={{ color: colors.textDim, textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 500 }}>
                Fehler-ID
              </span>
              <span style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace", color: colors.text }}>
                {error.digest ?? "nicht verfügbar"}
              </span>
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
              <button
                type="button"
                onClick={() => reset()}
                style={{
                  appearance: "none",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "0.625rem 1.25rem",
                  borderRadius: "9999px",
                  border: "none",
                  background: colors.orange,
                  color: "#FFFFFF",
                  fontSize: "0.875rem",
                  fontWeight: 600,
                }}
              >
                Erneut versuchen
              </button>
              <a
                href="/"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "0.625rem 1.25rem",
                  borderRadius: "9999px",
                  border: `1px solid #2A5656`,
                  color: colors.text,
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  textDecoration: "none",
                }}
              >
                Zur Startseite
              </a>
            </div>

            <p
              style={{
                margin: "1.5rem 0 0",
                paddingTop: "1rem",
                borderTop: `1px solid ${colors.border}`,
                color: colors.textDim,
                fontSize: "0.75rem",
                lineHeight: 1.5,
              }}
            >
              Hinweis: GridCheck liefert vorläufige Diagnosen. Eine rechtsverbindliche
              Netzanschlussprüfung erfolgt ausschließlich durch den zuständigen
              Netzbetreiber.
            </p>
          </div>
        </main>
      </body>
    </html>
  );
}
