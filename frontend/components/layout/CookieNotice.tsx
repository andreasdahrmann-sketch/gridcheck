"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  acknowledgeCookieNotice,
  hasAnalyticsConsent,
  hasCookieNoticeAcknowledged,
  setAnalyticsConsent,
} from "@/lib/cookie-consent";

export function CookieNotice() {
  const [visible, setVisible] = useState(false);
  const [analyticsOptIn, setAnalyticsOptIn] = useState(false);

  useEffect(() => {
    if (!hasCookieNoticeAcknowledged()) {
      setVisible(true);
      setAnalyticsOptIn(hasAnalyticsConsent());
    }
  }, []);

  if (!visible) {
    return null;
  }

  const acknowledge = () => {
    acknowledgeCookieNotice();
    setAnalyticsConsent(analyticsOptIn);
    setVisible(false);
  };

  return (
    <div
      role="dialog"
      aria-live="polite"
      aria-label="Hinweis zu Cookies"
      className="safe-area-bottom fixed inset-x-0 bottom-0 z-50 border-t border-white/10 bg-bg/95 p-4 shadow-lg backdrop-blur sm:p-5"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <p className="text-sm leading-relaxed text-text-muted">
            Wir verwenden technisch notwendige Cookies und lokale Speicher fuer Anmeldung, Sicherheit und
            grundlegende Einstellungen. Optionale Nutzungsstatistik (Conversion-Events) wird nur nach Ihrer
            Einwilligung gesendet. Details in der{" "}
            <Link href="/datenschutz" className="text-brand-cyan underline-offset-2 hover:underline">
              Datenschutzerklaerung
            </Link>
            .
          </p>
          <label className="flex cursor-pointer items-start gap-2 text-sm text-text-muted">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 rounded border-white/20 bg-white/5"
              checked={analyticsOptIn}
              onChange={(e) => setAnalyticsOptIn(e.target.checked)}
            />
            <span>Optionale Nutzungsstatistik erlauben (kein Werbe-Tracking, keine Drittanbieter-Cookies im MVP)</span>
          </label>
        </div>
        <button
          type="button"
          onClick={acknowledge}
          className="shrink-0 rounded-md bg-brand-cyan px-4 py-2 text-sm font-medium text-brand-bg transition-opacity hover:opacity-90"
        >
          Auswahl speichern
        </button>
      </div>
    </div>
  );
}
