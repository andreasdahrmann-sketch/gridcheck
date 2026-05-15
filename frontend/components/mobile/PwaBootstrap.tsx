"use client";

import { useEffect } from "react";
import { applyNativeShellChrome } from "@/lib/mobile/capacitor";

export function PwaBootstrap() {
  useEffect(() => {
    void applyNativeShellChrome();

    if (process.env.NODE_ENV !== "production") {
      return;
    }
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
      return;
    }

    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch((error) => {
      console.error("GridCheck service worker registration failed.", error);
    });
  }, []);

  return null;
}
