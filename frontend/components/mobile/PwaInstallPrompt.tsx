"use client";

import { Download, Share2, Smartphone } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { isNativeShell } from "@/lib/mobile/capacitor";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};

type PwaInstallPromptProps = {
  className?: string;
  compact?: boolean;
};

function detectIosSafari() {
  if (typeof window === "undefined") {
    return false;
  }

  const userAgent = window.navigator.userAgent;
  const isAppleMobile =
    /iPhone|iPad|iPod/.test(userAgent) ||
    (/Macintosh/.test(userAgent) && typeof navigator !== "undefined" && navigator.maxTouchPoints > 1);
  const isSafari = /Safari/.test(userAgent) && !/CriOS|FxiOS|EdgiOS/.test(userAgent);

  return isAppleMobile && isSafari;
}

function isStandaloneDisplayMode() {
  if (typeof window === "undefined") {
    return false;
  }

  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

export function PwaInstallPrompt({ className, compact = false }: PwaInstallPromptProps) {
  const [installEvent, setInstallEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [nativeShell, setNativeShell] = useState(false);
  const [standalone, setStandalone] = useState(false);
  const [iosSafari, setIosSafari] = useState(false);

  useEffect(() => {
    setNativeShell(isNativeShell());
    setStandalone(isStandaloneDisplayMode());
    setIosSafari(detectIosSafari());

    const handleBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setInstallEvent(event as BeforeInstallPromptEvent);
    };

    const handleInstalled = () => {
      setInstallEvent(null);
      setStandalone(true);
      setDialogOpen(false);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  const shouldRender = useMemo(() => {
    if (nativeShell) {
      return false;
    }
    if (standalone) {
      return false;
    }
    return Boolean(installEvent) || iosSafari;
  }, [installEvent, iosSafari, nativeShell, standalone]);

  async function handleInstallClick() {
    if (installEvent) {
      await installEvent.prompt();
      const choice = await installEvent.userChoice;
      if (choice.outcome !== "accepted") {
        return;
      }
      setInstallEvent(null);
      return;
    }

    setDialogOpen(true);
  }

  if (!shouldRender) {
    return null;
  }

  if (compact) {
    return (
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <Button
          type="button"
          onClick={handleInstallClick}
          className={className ?? "h-10 w-10 rounded-xl bg-brand-cyan px-0 text-slate-950 hover:bg-brand-cyan/90"}
        >
          {iosSafari ? <Share2 className="h-4 w-4" /> : <Download className="h-4 w-4" />}
          <span className="sr-only">App installieren</span>
        </Button>
        <DialogContent className="border border-white/10 bg-bg text-white">
          <DialogHeader>
            <DialogTitle>GridCheck auf dem Homescreen</DialogTitle>
            <DialogDescription className="text-text-muted">
              Auf iPhone/iPad laeuft die Installation ueber Safari direkt in den Homescreen.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 text-sm text-text-muted">
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="font-medium text-white">1. Teilen oeffnen</p>
              <p className="mt-1">Tippe in Safari auf das Teilen-Symbol.</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="font-medium text-white">2. &quot;Zum Home-Bildschirm&quot;</p>
              <p className="mt-1">Waehle den Eintrag fuer die Installation als Web-App.</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="font-medium text-white">3. Feldmodus starten</p>
              <p className="mt-1">Danach oeffnet GridCheck ohne Browserleisten im App-Look.</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
      <Button
        type="button"
        onClick={handleInstallClick}
        className={
          className ??
          "h-10 rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-4 text-brand-cyan hover:bg-brand-cyan/15"
        }
      >
        {iosSafari ? <Share2 className="mr-2 h-4 w-4" /> : <Download className="mr-2 h-4 w-4" />}
        App installieren
      </Button>
      <DialogContent className="border border-white/10 bg-bg text-white">
        <DialogHeader>
          <DialogTitle>GridCheck mobil installieren</DialogTitle>
          <DialogDescription className="text-text-muted">
            Die aktuelle Bereitstellung ist als installierbare PWA fuer Feldaufnahme und Tablet-Nutzung vorbereitet.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 text-sm text-text-muted">
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
            <p className="flex items-center gap-2 font-medium text-white">
              <Smartphone className="h-4 w-4 text-brand-cyan" />
              Android
            </p>
            <p className="mt-1">Chrome bietet die Installation direkt ueber den angezeigten Installieren-Dialog an.</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
            <p className="flex items-center gap-2 font-medium text-white">
              <Share2 className="h-4 w-4 text-brand-orange" />
              iPhone / iPad
            </p>
            <p className="mt-1">In Safari ueber Teilen → Zum Home-Bildschirm installieren.</p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
