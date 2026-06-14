"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { logout, me } from "@/lib/api/auth";
import { useIdleLogout } from "@/hooks/useIdleLogout";

const DEFAULT_TIMEOUT_MS = 10 * 60 * 1000;

function readConfiguredTimeoutMs(): number {
  const raw = process.env.NEXT_PUBLIC_IDLE_LOGOUT_MS;
  if (!raw) return DEFAULT_TIMEOUT_MS;
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return DEFAULT_TIMEOUT_MS;
  return parsed;
}

/**
 * Mountet einmalig den Idle-Logout-Timer. Aktiviert sich nur, wenn /me einen
 * eingeloggten User liefert. Nach `timeoutMs` Inaktivitaet wird /logout
 * aufgerufen (Backend loescht Access-, Refresh- und CSRF-Cookies) und der
 * Browser nach /login redirected.
 *
 * Beachten:
 * - Keine Geschaeftslogik, kein State-Management; nur Session-Lebenszyklus.
 * - Backend-/Logout-Endpoint loescht den Refresh-Cookie -> nach Reload
 *   landet der User korrekt auf /login.
 */
export function IdleLogoutGate() {
  const router = useRouter();
  const pathname = usePathname();
  const [isLoggedIn, setIsLoggedIn] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    me()
      .then(() => {
        if (active) setIsLoggedIn(true);
      })
      .catch(() => {
        if (active) setIsLoggedIn(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useIdleLogout({
    enabled: isLoggedIn === true,
    timeoutMs: readConfiguredTimeoutMs(),
    onTimeout: () => {
      void (async () => {
        try {
          await logout();
        } catch {
          // logout darf nicht blocken - Redirect erfolgt trotzdem
        } finally {
          setIsLoggedIn(false);
          const target = pathname && pathname !== "/login" ? pathname : "/";
          const next = encodeURIComponent(target);
          router.replace(`/login?reason=idle&next=${next}`);
        }
      })();
    },
  });

  return null;
}