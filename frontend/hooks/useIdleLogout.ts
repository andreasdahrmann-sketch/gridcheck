"use client";

import { useEffect, useRef } from "react";

export type UseIdleLogoutOptions = {
  enabled: boolean;
  timeoutMs?: number;
  onTimeout: () => void;
};

const DEFAULT_TIMEOUT_MS = 10 * 60 * 1000;
const MOUSEMOVE_DEBOUNCE_MS = 1000;

const ACTIVITY_EVENTS: ReadonlyArray<keyof WindowEventMap> = [
  "keydown",
  "click",
  "scroll",
  "touchstart",
];

export function useIdleLogout({ enabled, timeoutMs, onTimeout }: UseIdleLogoutOptions): void {
  const onTimeoutRef = useRef(onTimeout);
  onTimeoutRef.current = onTimeout;

  useEffect(() => {
    if (!enabled) return;
    if (typeof window === "undefined") return;

    const effectiveTimeout =
      typeof timeoutMs === "number" && timeoutMs > 0 ? timeoutMs : DEFAULT_TIMEOUT_MS;

    let timer: ReturnType<typeof setTimeout> | null = null;
    let lastMouseMove = 0;
    let timedOut = false;

    const fireTimeout = () => {
      if (timedOut) return;
      timedOut = true;
      try {
        onTimeoutRef.current();
      } catch {
        // swallow - caller's logout must not crash the hook
      }
    };

    const resetTimer = () => {
      if (timedOut) return;
      if (timer) clearTimeout(timer);
      timer = setTimeout(fireTimeout, effectiveTimeout);
    };

    const handleMouseMove = () => {
      const now = Date.now();
      if (now - lastMouseMove < MOUSEMOVE_DEBOUNCE_MS) return;
      lastMouseMove = now;
      resetTimer();
    };

    // visibilitychange: nur loggen / Sanity, KEINEN Timer-Reset, sonst
    // wuerde ein Tab-Wechsel zurueck die Idle-Zeit kuenstlich verlaengern.
    const handleVisibility = () => {
      /* intentional no-op: do not reset the timer on tab focus */
    };

    for (const event of ACTIVITY_EVENTS) {
      window.addEventListener(event, resetTimer, { passive: true });
    }
    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    document.addEventListener("visibilitychange", handleVisibility);

    resetTimer();

    return () => {
      if (timer) clearTimeout(timer);
      for (const event of ACTIVITY_EVENTS) {
        window.removeEventListener(event, resetTimer);
      }
      window.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [enabled, timeoutMs]);
}