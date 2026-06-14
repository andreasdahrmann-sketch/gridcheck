/**
 * Cookie- / Consent-Verwaltung gemaess TTDSG § 25 + DSGVO Art. 6 Abs. 1 lit. a.
 *
 * Vor erteilter Einwilligung duerfen ausschliesslich technisch notwendige
 * Cookies / lokale Speicher gesetzt werden. Analytics / Marketing / Drittanbieter
 * werden erst nach Opt-In aktiviert.
 *
 * Das Consent-Objekt wird unter dem versionierten Key
 *   gridcheck_cookie_consent_v1
 * persistiert. Bei Schema-Aenderungen muss der Key-Suffix erhoeht werden,
 * damit alte Consents nicht stillschweigend uebernommen werden (DSGVO-konform).
 */

import { useEffect, useState } from "react";

export const CONSENT_STORAGE_KEY = "gridcheck_cookie_consent_v1";
export const CONSENT_SCHEMA_VERSION = 1;

/** Event-Name fuer In-Tab Updates des Consent-State. */
const CONSENT_EVENT = "gridcheck:consent-changed";

export type CookieCategory = "essential" | "analytics" | "marketing";

export type CookieConsent = {
  /** Schema-Version, um spaetere Migrationen zu erlauben. */
  version: number;
  /** Technisch notwendig, immer true. */
  essential: true;
  /** Reichweitenmessung / Conversion-Events / Sentry o.ae. */
  analytics: boolean;
  /** Marketing-/Retargeting-Cookies (im MVP nicht aktiv). */
  marketing: boolean;
  /** ISO-8601 Zeitpunkt der Erteilung. */
  timestamp: string;
};

const DEFAULT_DENY: Omit<CookieConsent, "timestamp"> = {
  version: CONSENT_SCHEMA_VERSION,
  essential: true,
  analytics: false,
  marketing: false,
};

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

/** Liest das gespeicherte Consent-Objekt, oder null falls keines existiert / ungueltig. */
export function getStoredConsent(): CookieConsent | null {
  if (!isBrowser()) return null;
  try {
    const raw = window.localStorage.getItem(CONSENT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<CookieConsent>;
    if (
      parsed &&
      parsed.version === CONSENT_SCHEMA_VERSION &&
      typeof parsed.timestamp === "string" &&
      parsed.essential === true
    ) {
      return {
        version: CONSENT_SCHEMA_VERSION,
        essential: true,
        analytics: Boolean(parsed.analytics),
        marketing: Boolean(parsed.marketing),
        timestamp: parsed.timestamp,
      };
    }
    return null;
  } catch {
    return null;
  }
}

export function hasValidConsent(): boolean {
  return getStoredConsent() !== null;
}

/** Persistiert ein Consent-Objekt und benachrichtigt alle aktiven Komponenten. */
export function writeConsent(partial: { analytics: boolean; marketing: boolean }): CookieConsent {
  const consent: CookieConsent = {
    ...DEFAULT_DENY,
    analytics: partial.analytics,
    marketing: partial.marketing,
    timestamp: new Date().toISOString(),
  };
  if (isBrowser()) {
    try {
      window.localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(consent));
      window.dispatchEvent(new CustomEvent(CONSENT_EVENT, { detail: consent }));
    } catch {
      /* localStorage unavailable */
    }
  }
  return consent;
}

/** Reset/Widerruf — entfernt jeden gespeicherten Consent (zeigt Banner erneut). */
export function revokeConsent(): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.removeItem(CONSENT_STORAGE_KEY);
    window.dispatchEvent(new CustomEvent(CONSENT_EVENT, { detail: null }));
  } catch {
    /* localStorage unavailable */
  }
}

export function acceptAll(): CookieConsent {
  return writeConsent({ analytics: true, marketing: true });
}

export function acceptEssentialOnly(): CookieConsent {
  return writeConsent({ analytics: false, marketing: false });
}

/** True nur wenn ein gueltiger Consent existiert UND analytics darin opt-in ist. */
export function hasAnalyticsConsent(): boolean {
  const c = getStoredConsent();
  return c !== null && c.analytics === true;
}

export function hasMarketingConsent(): boolean {
  const c = getStoredConsent();
  return c !== null && c.marketing === true;
}

/**
 * React-Hook fuer alle Komponenten, die ihren Consent-Status reaktiv brauchen.
 * Gibt das aktuelle Consent-Objekt zurueck (oder null = noch keine Entscheidung).
 */
export function useCookieConsent(): {
  consent: CookieConsent | null;
  isReady: boolean;
  acceptAll: () => void;
  acceptEssentialOnly: () => void;
  setCategories: (analytics: boolean, marketing: boolean) => void;
  revoke: () => void;
} {
  const [consent, setConsent] = useState<CookieConsent | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setConsent(getStoredConsent());
    setIsReady(true);

    const onChange = (event: Event) => {
      const detail = (event as CustomEvent<CookieConsent | null>).detail ?? getStoredConsent();
      setConsent(detail);
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key === CONSENT_STORAGE_KEY) {
        setConsent(getStoredConsent());
      }
    };
    window.addEventListener(CONSENT_EVENT, onChange);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(CONSENT_EVENT, onChange);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  return {
    consent,
    isReady,
    acceptAll: () => setConsent(acceptAll()),
    acceptEssentialOnly: () => setConsent(acceptEssentialOnly()),
    setCategories: (analytics, marketing) => setConsent(writeConsent({ analytics, marketing })),
    revoke: () => {
      revokeConsent();
      setConsent(null);
    },
  };
}

// ---------------------------------------------------------------------------
// Backwards-Compat fuer bestehende Aufrufer (lib/api/analytics.ts u.a.)
// ---------------------------------------------------------------------------

/**
 * @deprecated nur fuer Migration; bitte useCookieConsent() oder hasAnalyticsConsent() nutzen.
 */
export function hasCookieNoticeAcknowledged(): boolean {
  return hasValidConsent();
}

/**
 * @deprecated nur fuer Migration; verwendet jetzt das v1-Consent-Schema.
 */
export function acknowledgeCookieNotice(): void {
  acceptEssentialOnly();
}

/**
 * @deprecated nur fuer Migration; setzt analytics-Flag im neuen Schema.
 */
export function setAnalyticsConsent(allowed: boolean): void {
  writeConsent({ analytics: allowed, marketing: hasMarketingConsent() });
}
