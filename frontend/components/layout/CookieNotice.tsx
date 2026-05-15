"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const STORAGE_KEY = "gridcheck_cookie_notice_ack";

export function CookieNotice() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (localStorage.getItem(STORAGE_KEY) !== "1") {
        setVisible(true);
      }
    } catch {
      setVisible(true);
    }
  }, []);

  if (!visible) {
    return null;
  }

  const acknowledge = () => {
    try {
      localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      /* localStorage unavailable */
    }
    setVisible(false);
  };

  return (
    <div
      role="dialog"
      aria-live="polite"
      aria-label="Hinweis zu Cookies"
      className="safe-area-bottom fixed inset-x-0 bottom-0 z-50 border-t border-white/10 bg-bg/95 p-4 shadow-lg backdrop-blur sm:p-5"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm leading-relaxed text-text-muted">
          Wir verwenden nur technisch notwendige Cookies und lokale Speicher fuer Anmeldung, Sicherheit und
          grundlegende Einstellungen. Optionale Analyse-Cookies sind derzeit nicht aktiv. Details in der{" "}
          <Link href="/datenschutz" className="text-brand-cyan underline-offset-2 hover:underline">
            Datenschutzerklaerung
          </Link>
          .
        </p>
        <button
          type="button"
          onClick={acknowledge}
          className="shrink-0 rounded-md bg-brand-cyan px-4 py-2 text-sm font-medium text-brand-bg transition-opacity hover:opacity-90"
        >
          Verstanden
        </button>
      </div>
    </div>
  );
}
