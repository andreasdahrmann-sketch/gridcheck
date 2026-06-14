"use client";

import { ReactNode, useEffect, useState } from "react";
import { notFound } from "next/navigation";
import { me, type AuthUser } from "@/lib/api/auth";
import { isBillingEnabled } from "@/lib/billing-flag";

type GateState = "checking" | "allowed" | "blocked";

/**
 * Client-Side Gate fuer Billing-bezogene Seiten.
 *
 * Verhalten:
 *   - `BILLING_ENABLED=true` → Inhalt sofort sichtbar, kein Auth-Roundtrip.
 *   - `BILLING_ENABLED=false` → Auth-/Admin-Pruefung; Admins sehen Inhalt,
 *     alle anderen bekommen ein echtes 404 (nicht 503), damit die Existenz
 *     der Route fuer nicht-admins verborgen bleibt.
 *
 * Sicherheitsgrenze bleibt das Backend (`require_billing_enabled_or_admin`).
 * Diese Komponente ist nur eine UX-Schicht.
 */
export function BillingGate({ children }: { children: ReactNode }) {
  const enabled = isBillingEnabled();
  const [state, setState] = useState<GateState>(enabled ? "allowed" : "checking");

  useEffect(() => {
    if (enabled) {
      return;
    }
    let active = true;
    me()
      .then((user: AuthUser | null) => {
        if (!active) return;
        if (user?.is_admin) {
          setState("allowed");
        } else {
          setState("blocked");
        }
      })
      .catch(() => {
        if (active) {
          setState("blocked");
        }
      });
    return () => {
      active = false;
    };
  }, [enabled]);

  if (state === "blocked") {
    notFound();
  }

  if (state === "checking") {
    return null;
  }

  return <>{children}</>;
}
