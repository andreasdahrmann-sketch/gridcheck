"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  acceptAll,
  acceptEssentialOnly,
  getStoredConsent,
  hasValidConsent,
  writeConsent,
} from "@/lib/cookie-consent";

/**
 * TTDSG- / DSGVO-konformes Consent-Banner.
 *
 * Verhalten:
 *  - Banner erscheint NUR, wenn unter `gridcheck_cookie_consent_v1` noch kein
 *    gueltiger Consent gespeichert ist.
 *  - Drei Pfade: "Alle akzeptieren", "Nur essenzielle", "Einstellungen".
 *  - Solange kein Opt-In erteilt ist, duerfen weder Analytics, Sentry,
 *    Marketing-Cookies noch andere nicht-essenzielle Tracker geladen werden
 *    (siehe `lib/api/analytics.ts`, das vor jedem Send `hasAnalyticsConsent()`
 *    prueft).
 *  - "Einstellungen" oeffnet ein Modal mit drei Toggles (essenziell read-only,
 *    Analytics, Marketing).
 */
export function CookieNotice() {
  const [visible, setVisible] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [analyticsOn, setAnalyticsOn] = useState(false);
  const [marketingOn, setMarketingOn] = useState(false);

  useEffect(() => {
    if (!hasValidConsent()) {
      setVisible(true);
      const existing = getStoredConsent();
      if (existing) {
        setAnalyticsOn(existing.analytics);
        setMarketingOn(existing.marketing);
      }
    }
  }, []);

  if (!visible) return null;

  const handleAcceptAll = () => {
    acceptAll();
    setVisible(false);
    setShowSettings(false);
  };

  const handleEssentialOnly = () => {
    acceptEssentialOnly();
    setVisible(false);
    setShowSettings(false);
  };

  const handleSaveCustom = () => {
    writeConsent({ analytics: analyticsOn, marketing: marketingOn });
    setVisible(false);
    setShowSettings(false);
  };

  return (
    <>
      <div
        role="dialog"
        aria-modal="false"
        aria-live="polite"
        aria-label="Hinweis zu Cookies und lokaler Speicherung"
        className="safe-area-bottom fixed inset-x-0 bottom-0 z-50 border-t border-white/10 bg-bg/95 p-4 shadow-lg backdrop-blur sm:p-5"
      >
        <div className="mx-auto flex max-w-6xl flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <p className="text-sm font-semibold text-white">Datenschutz-Einstellungen</p>
            <p className="text-sm leading-relaxed text-text-muted">
              Wir verwenden technisch notwendige Cookies und lokale Speicher fuer Anmeldung,
              Sicherheit und grundlegende Plattformfunktionen. Optionale Cookies fuer
              Reichweitenmessung und Marketing setzen wir <strong className="text-white">nur mit Ihrer
              ausdruecklichen Einwilligung</strong> (TTDSG &sect; 25, DSGVO Art. 6 Abs. 1 lit. a).
              Sie koennen Ihre Auswahl jederzeit in den Einstellungen widerrufen. Details in der{" "}
              <Link href="/datenschutz" className="text-brand-cyan underline-offset-2 hover:underline">
                Datenschutzerklaerung
              </Link>
              .
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center lg:shrink-0 lg:flex-nowrap">
            <button
              type="button"
              onClick={() => setShowSettings(true)}
              className="rounded-md border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-text-muted transition-colors hover:bg-white/10"
            >
              Einstellungen
            </button>
            <button
              type="button"
              onClick={handleEssentialOnly}
              className="rounded-md border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-text-muted transition-colors hover:bg-white/10"
            >
              Nur essenzielle
            </button>
            <button
              type="button"
              onClick={handleAcceptAll}
              className="rounded-md bg-brand-cyan px-4 py-2 text-sm font-semibold text-brand-bg transition-opacity hover:opacity-90"
            >
              Alle akzeptieren
            </button>
          </div>
        </div>
      </div>

      {showSettings && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="cookie-settings-title"
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4 backdrop-blur"
        >
          <div className="w-full max-w-lg rounded-2xl border border-white/10 bg-bg p-6 shadow-2xl">
            <h2 id="cookie-settings-title" className="text-lg font-semibold text-white">
              Cookie- und Tracking-Einstellungen
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-text-muted">
              Bitte waehlen Sie aus, welche Datenverarbeitung Sie zulassen moechten. Essenzielle
              Cookies sind fuer den Betrieb der Plattform technisch erforderlich und nicht
              abwaehlbar.
            </p>

            <div className="mt-5 space-y-4">
              <ConsentRow
                title="Essenziell"
                description="Anmeldung, Sicherheits-Token (CSRF), Sitzungs- und Spracheinstellungen. Rechtsgrundlage: TTDSG § 25 Abs. 2 Nr. 2 / Art. 6 Abs. 1 lit. b DSGVO."
                checked
                disabled
                onChange={() => undefined}
              />
              <ConsentRow
                title="Statistik / Reichweitenmessung"
                description="Anonymisierte Conversion-Events (z. B. abgeschlossene Analysen) fuer Produktverbesserung. Erst nach Einwilligung. Rechtsgrundlage: Art. 6 Abs. 1 lit. a DSGVO."
                checked={analyticsOn}
                disabled={false}
                onChange={(v) => setAnalyticsOn(v)}
              />
              <ConsentRow
                title="Marketing"
                description="Im aktuellen Build nicht aktiv eingebunden. Toggle bleibt nur als Vorbereitung; ohne aktiven Einsatz wird kein Tracker geladen."
                checked={marketingOn}
                disabled={false}
                onChange={(v) => setMarketingOn(v)}
              />
            </div>

            <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() => setShowSettings(false)}
                className="rounded-md border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-text-muted transition-colors hover:bg-white/10"
              >
                Abbrechen
              </button>
              <button
                type="button"
                onClick={handleEssentialOnly}
                className="rounded-md border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-text-muted transition-colors hover:bg-white/10"
              >
                Nur essenzielle
              </button>
              <button
                type="button"
                onClick={handleSaveCustom}
                className="rounded-md bg-brand-cyan px-4 py-2 text-sm font-semibold text-brand-bg transition-opacity hover:opacity-90"
              >
                Auswahl speichern
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ConsentRow({
  title,
  description,
  checked,
  disabled,
  onChange,
}: {
  title: string;
  description: string;
  checked: boolean;
  disabled: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <label
      className={`flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-3 ${
        disabled ? "opacity-80" : "cursor-pointer hover:bg-white/10"
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 h-4 w-4 rounded border-white/20 bg-white/5"
      />
      <span className="space-y-1">
        <span className="block text-sm font-medium text-white">
          {title}
          {disabled && (
            <span className="ml-2 rounded-full border border-white/20 bg-white/10 px-2 py-0.5 text-[10px] uppercase tracking-wider text-text-dim">
              Pflicht
            </span>
          )}
        </span>
        <span className="block text-xs leading-5 text-text-muted">{description}</span>
      </span>
    </label>
  );
}
