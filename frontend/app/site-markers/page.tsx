"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ChangeEvent, FormEvent, Suspense, useEffect, useMemo, useState } from "react";
import { Camera, Crosshair, ShieldAlert, Smartphone } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  SiteMarkerApiError,
  createSiteMarker,
  getSiteMarkerPhotoUrl,
  listSiteMarkers,
  type SiteMarker,
  type SiteMarkerAssetType,
  type SiteMarkerLocationSource,
} from "@/lib/api/site-markers";
import { parseSiteMarkerFlowContext } from "@/lib/app-flow";
import { captureSiteMarkerPhoto, getCurrentSiteMarkerPosition, isNativeShell } from "@/lib/mobile/capacitor";

const SiteMarkerLeafletMap = dynamic(() => import("@/components/site-markers/SiteMarkerLeafletMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[320px] items-center justify-center rounded-[24px] border border-white/10 bg-black/20 text-sm text-text-muted sm:h-[360px]">
      Lade Feldkarte...
    </div>
  ),
});

const ASSET_TYPE_OPTIONS: { value: SiteMarkerAssetType; label: string }[] = [
  { value: "ortsnetztrafo", label: "Ortsnetztrafo" },
  { value: "umspannwerk", label: "Umspannwerk" },
  { value: "schaltstation", label: "Schaltstation" },
];

const LOCATION_SOURCE_OPTIONS: { value: SiteMarkerLocationSource; label: string }[] = [
  { value: "gps", label: "GPS am Standort" },
  { value: "manual", label: "Manuelle Koordinate" },
];

const SITE_MARKER_DRAFT_KEY = "gridcheck.site-marker-draft.v1";
const SITE_MARKER_CACHE_KEY = "gridcheck.site-marker-cache.v1";
const cardClass = "rounded-[24px] border border-border/70 bg-bg-card/80 shadow-[0_12px_42px_rgba(0,0,0,0.18)]";
const fieldClass =
  "h-11 rounded-xl border-border/70 bg-white/5 px-3 text-white placeholder:text-text-dim focus-visible:border-brand-cyan/70 focus-visible:ring-brand-cyan/20";

type SiteMarkerDraft = {
  assetType: SiteMarkerAssetType;
  locationSource: SiteMarkerLocationSource;
  latitude: string;
  longitude: string;
  gpsAccuracyM?: number | null;
  lastLocationAt?: string | null;
};

function formatCoordinate(value: number) {
  return value.toFixed(6);
}

function formatAssetType(assetType: SiteMarkerAssetType) {
  return ASSET_TYPE_OPTIONS.find((option) => option.value === assetType)?.label ?? assetType;
}

function formatAccuracy(value: number | null) {
  if (!value) {
    return "Noch keine GPS-Genauigkeit";
  }
  if (value < 20) {
    return `ca. ${Math.round(value)} m`;
  }
  return `ca. ${Math.round(value)} m (vorsichtig pruefen)`;
}

function readCoordinate(raw: string) {
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function isSupportedAssetType(value?: string) {
  return Boolean(value && ASSET_TYPE_OPTIONS.some((option) => option.value === value));
}

function SiteMarkersPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [assetType, setAssetType] = useState<SiteMarkerAssetType>("ortsnetztrafo");
  const [locationSource, setLocationSource] = useState<SiteMarkerLocationSource>("gps");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);
  const [uiMessage, setUiMessage] = useState<string | null>(null);
  const [uiError, setUiError] = useState<string | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [isCapturingNativePhoto, setIsCapturingNativePhoto] = useState(false);
  const [isNativeShellActive, setIsNativeShellActive] = useState(false);
  const [gpsAccuracyM, setGpsAccuracyM] = useState<number | null>(null);
  const [lastLocationAt, setLastLocationAt] = useState<string | null>(null);
  const [cachedMarkers, setCachedMarkers] = useState<SiteMarker[]>([]);
  const [isOnline, setIsOnline] = useState(true);
  const [contextApplied, setContextApplied] = useState(false);
  const queryClient = useQueryClient();
  const markerContext = useMemo(() => parseSiteMarkerFlowContext(searchParams), [searchParams]);

  const markersQuery = useQuery<SiteMarker[]>({
    queryKey: ["site-markers"],
    queryFn: listSiteMarkers,
  });

  const createMutation = useMutation({
    mutationFn: createSiteMarker,
    onSuccess: (marker) => {
      setUiError(null);
      setUiMessage(`Marker fuer ${formatAssetType(marker.asset_type)} gespeichert.`);
      setPhoto(null);
      setPhotoPreviewUrl(null);
      setCachedMarkers((current) => [marker, ...current.filter((item) => item.id !== marker.id)]);
      queryClient.setQueryData<SiteMarker[]>(["site-markers"], (current = []) => [
        marker,
        ...current.filter((item) => item.id !== marker.id),
      ]);
      queryClient.invalidateQueries({ queryKey: ["site-markers"] });
    },
    onError: (error) => {
      setUiError(error instanceof Error ? error.message : "Marker konnte nicht gespeichert werden.");
    },
  });

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    setIsNativeShellActive(isNativeShell());
    setIsOnline(window.navigator.onLine);

    try {
      const rawDraft = window.localStorage.getItem(SITE_MARKER_DRAFT_KEY);
      if (rawDraft) {
        const draft = JSON.parse(rawDraft) as Partial<SiteMarkerDraft>;
        if (draft.assetType) setAssetType(draft.assetType);
        if (draft.locationSource) setLocationSource(draft.locationSource);
        if (typeof draft.latitude === "string") setLatitude(draft.latitude);
        if (typeof draft.longitude === "string") setLongitude(draft.longitude);
        if (typeof draft.gpsAccuracyM === "number") setGpsAccuracyM(draft.gpsAccuracyM);
        if (typeof draft.lastLocationAt === "string") setLastLocationAt(draft.lastLocationAt);
      }
    } catch {
      // Entwurf ist optional; bei defektem Storage ignorieren wir den lokalen Zustand.
    }

    try {
      const rawCache = window.localStorage.getItem(SITE_MARKER_CACHE_KEY);
      if (rawCache) {
        setCachedMarkers(JSON.parse(rawCache) as SiteMarker[]);
      }
    } catch {
      // Marker-Cache ist nur eine Offline-Hilfe.
    }

    const handleOnlineState = () => setIsOnline(window.navigator.onLine);
    window.addEventListener("online", handleOnlineState);
    window.addEventListener("offline", handleOnlineState);

    return () => {
      window.removeEventListener("online", handleOnlineState);
      window.removeEventListener("offline", handleOnlineState);
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const draft: SiteMarkerDraft = {
      assetType,
      locationSource,
      latitude,
      longitude,
      gpsAccuracyM,
      lastLocationAt,
    };

    window.localStorage.setItem(SITE_MARKER_DRAFT_KEY, JSON.stringify(draft));
  }, [assetType, gpsAccuracyM, lastLocationAt, latitude, locationSource, longitude]);

  useEffect(() => {
    if (typeof window === "undefined" || !markersQuery.data) {
      return;
    }

    setCachedMarkers(markersQuery.data);
    window.localStorage.setItem(SITE_MARKER_CACHE_KEY, JSON.stringify(markersQuery.data));
  }, [markersQuery.data]);

  useEffect(() => {
    if (!photo) {
      setPhotoPreviewUrl(null);
      return;
    }

    const nextPreviewUrl = URL.createObjectURL(photo);
    setPhotoPreviewUrl(nextPreviewUrl);

    return () => {
      URL.revokeObjectURL(nextPreviewUrl);
    };
  }, [photo]);

  useEffect(() => {
    if (!markersQuery.isError) {
      return;
    }

    if (markersQuery.error instanceof SiteMarkerApiError && markersQuery.error.status === 401) {
      router.replace("/login");
    }
  }, [markersQuery.error, markersQuery.isError, router]);

  useEffect(() => {
    if (contextApplied) {
      return;
    }

    const hasFlowContext = Boolean(
      markerContext.projectId ||
        markerContext.projectName ||
        markerContext.plz ||
        markerContext.ort ||
        markerContext.latitude !== undefined ||
        markerContext.longitude !== undefined ||
        markerContext.assetType
    );

    if (!hasFlowContext) {
      setContextApplied(true);
      return;
    }

    if (!latitude && markerContext.latitude !== undefined) {
      setLatitude(formatCoordinate(markerContext.latitude));
    }
    if (!longitude && markerContext.longitude !== undefined) {
      setLongitude(formatCoordinate(markerContext.longitude));
    }
    if (
      !lastLocationAt &&
      (markerContext.latitude !== undefined || markerContext.longitude !== undefined) &&
      !latitude &&
      !longitude
    ) {
      setLastLocationAt(new Date().toISOString());
      setLocationSource("manual");
    }
    if (assetType === "ortsnetztrafo" && isSupportedAssetType(markerContext.assetType)) {
      setAssetType(markerContext.assetType as SiteMarkerAssetType);
    }

    setContextApplied(true);
  }, [assetType, contextApplied, lastLocationAt, latitude, longitude, markerContext]);

  function resetStatus() {
    setUiMessage(null);
    setUiError(null);
  }

  function handlePhotoChange(event: ChangeEvent<HTMLInputElement>) {
    resetStatus();
    setPhoto(event.target.files?.[0] ?? null);
  }

  function handleCoordinateChange(kind: "latitude" | "longitude", value: string) {
    resetStatus();
    setLocationSource("manual");
    if (kind === "latitude") {
      setLatitude(value);
      return;
    }
    setLongitude(value);
  }

  async function handleCaptureGps() {
    resetStatus();
    setIsLocating(true);

    try {
      const position = await getCurrentSiteMarkerPosition();
      setLatitude(position.latitude.toFixed(6));
      setLongitude(position.longitude.toFixed(6));
      setGpsAccuracyM(position.accuracy ?? null);
      setLastLocationAt(new Date().toISOString());
      setLocationSource("gps");
      setUiMessage(
        isNativeShellActive ? "Standort ueber nativen GPS-Pfad uebernommen." : "GPS-Standort uebernommen."
      );
    } catch (error) {
      setUiError(error instanceof Error ? error.message : "GPS-Standort konnte nicht erfasst werden.");
    } finally {
      setIsLocating(false);
    }
  }

  async function handleNativePhotoCapture() {
    resetStatus();
    setIsCapturingNativePhoto(true);

    try {
      const capturedPhoto = await captureSiteMarkerPhoto();
      if (!capturedPhoto) {
        setUiError("Native Kamera ist in diesem Laufzeitmodus nicht verfuegbar.");
        return;
      }

      setPhoto(capturedPhoto);
      setUiMessage("Foto ueber nativen Kamera-/Galerie-Pfad uebernommen.");
    } catch (error) {
      setUiError(error instanceof Error ? error.message : "Foto konnte nicht uebernommen werden.");
    } finally {
      setIsCapturingNativePhoto(false);
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    resetStatus();

    const parsedLatitude = readCoordinate(latitude);
    const parsedLongitude = readCoordinate(longitude);

    if (parsedLatitude === null || parsedLongitude === null) {
      setUiError("Bitte gueltige Koordinaten erfassen.");
      return;
    }
    if (parsedLatitude < -90 || parsedLatitude > 90 || parsedLongitude < -180 || parsedLongitude > 180) {
      setUiError("Breiten- und Laengengrad liegen ausserhalb des gueltigen Bereichs.");
      return;
    }
    if (!photo) {
      setUiError("Bitte ein Foto hochladen.");
      return;
    }

    try {
      await createMutation.mutateAsync({
        asset_type: assetType,
        location_source: locationSource,
        latitude: parsedLatitude,
        longitude: parsedLongitude,
        photo,
      });
    } catch {
      // Fehler werden zentral ueber onError in eine nutzernahe Meldung gemappt.
    }
  }

  const visibleMarkers = markersQuery.data ?? cachedMarkers;
  const hasCachedFallback = !markersQuery.data && cachedMarkers.length > 0;
  const hasMarkerContext = Boolean(
    markerContext.projectId ||
      markerContext.projectName ||
      markerContext.plz ||
      markerContext.ort ||
      markerContext.latitude !== undefined ||
      markerContext.longitude !== undefined
  );
  const listErrorMessage =
    markersQuery.isError && !(markersQuery.error instanceof SiteMarkerApiError && markersQuery.error.status === 401)
      ? markersQuery.error instanceof Error
        ? markersQuery.error.message
        : "Marker konnten nicht geladen werden."
      : null;
  const primaryContextHref = markerContext.projectId ? `/projects/${markerContext.projectId}` : markerContext.returnTo ?? "/";
  const primaryContextLabel = markerContext.projectId
    ? "Zur Projektanalyse"
    : markerContext.source === "check"
      ? "Zurueck zum Check"
      : "Zur Startseite";
  const contextLocationSummary = [markerContext.plz ? `PLZ ${markerContext.plz}` : null, markerContext.ort ?? null]
    .filter(Boolean)
    .join(" · ");
  const coordinatesPrefilled = markerContext.latitude !== undefined && markerContext.longitude !== undefined;

  const draftPosition = useMemo(() => {
    const parsedLatitude = readCoordinate(latitude);
    const parsedLongitude = readCoordinate(longitude);
    if (parsedLatitude === null || parsedLongitude === null) {
      return null;
    }

    return {
      latitude: parsedLatitude,
      longitude: parsedLongitude,
      accuracyM: gpsAccuracyM,
    };
  }, [gpsAccuracyM, latitude, longitude]);

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <section className="flex flex-col gap-3 border-b border-border/70 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.24em] text-brand-cyan">Feldaufnahme</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Vor-Ort-Marker</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-text-muted">
              Mobile Erfassung fuer sichtbare Netzassets mit Koordinate, Kamerafoto, lokalem Entwurf und bewusstem
              Status <span className="font-medium text-white">unverified</span>.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-text-muted">
            Installierbare Feldoberflaeche, aber weiterhin ohne automatische Netzkapazitaetsaussage.
          </div>
        </section>

        <section className="mt-6 grid gap-3 sm:grid-cols-3">
          {[
            {
              title: "PWA-ready",
              description: "Homescreen-Installation fuer Android und iPhone/iPad-Safari vorbereitet.",
              icon: Smartphone,
            },
            {
              title: "GPS + Kamera",
              description: "Rueckkamera wird auf mobilen Browsern direkt bevorzugt geoeffnet.",
              icon: Camera,
            },
            {
              title: "Feldtauglich",
              description: "Entwurf und letzte Marker bleiben bei Funkloch lokal sichtbar.",
              icon: ShieldAlert,
            },
          ].map((item) => (
            <div key={item.title} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
              <div className="flex items-center gap-2 text-white">
                <item.icon className="h-4 w-4 text-brand-cyan" />
                <p className="text-sm font-semibold">{item.title}</p>
              </div>
              <p className="mt-2 text-sm leading-6 text-text-muted">{item.description}</p>
            </div>
          ))}
        </section>

        {hasMarkerContext ? (
          <section className="mt-6 rounded-[24px] border border-brand-cyan/20 bg-brand-cyan/10 px-4 py-4 sm:px-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-sm font-semibold text-white">
                  Feldaufnahme im Kontext von {markerContext.projectName ?? "Ihrem aktuellen Vorgang"}
                </p>
                <p className="mt-2 text-sm leading-6 text-text-muted">
                  Dieser Marker-Flow ist als dokumentierende Vor-Ort-Ergaenzung gedacht. Sichtbare Assets,
                  Auffaelligkeiten und Standortindizien lassen sich mobil erfassen, ohne daraus automatisch freie
                  Netzkapazitaet abzuleiten.
                </p>
                <p className="mt-2 text-xs leading-5 text-text-dim">
                  {contextLocationSummary ? `${contextLocationSummary}. ` : ""}
                  {coordinatesPrefilled
                    ? "Vorhandene Projekt- oder Check-Koordinaten wurden fuer den Start vorbefuellt."
                    : "Koordinaten koennen per GPS uebernommen oder manuell gesetzt werden."}
                </p>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Link
                  href={primaryContextHref}
                  className="inline-flex h-11 items-center justify-center rounded-xl bg-brand-orange px-4 text-sm font-semibold text-white transition hover:bg-brand-orangeHover"
                >
                  {primaryContextLabel}
                </Link>
                <Link
                  href="/projects"
                  className="inline-flex h-11 items-center justify-center rounded-xl border border-white/15 bg-white/5 px-4 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  Projekt-Workspace
                </Link>
              </div>
            </div>
          </section>
        ) : null}

        {!isOnline ? (
          <div className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
            Kein Netz erkannt. Die Oberflaeche und lokale Entwuerfe bleiben nutzbar, Uploads brauchen aber wieder
            Verbindung.
          </div>
        ) : null}
        {isNativeShellActive ? (
          <div className="mt-6 rounded-2xl border border-brand-cyan/30 bg-brand-cyan/10 px-4 py-3 text-sm text-brand-cyan">
            Der native Shell ist aktiv. GPS und Kamera koennen fuer die Feldaufnahme bevorzugt ueber Capacitor genutzt
            werden; Web/PWA bleibt unveraendert der gleiche Hauptpfad.
          </div>
        ) : null}
        {uiMessage ? (
          <div className="mt-6 rounded-2xl border border-brand-cyan/30 bg-brand-cyan/10 px-4 py-3 text-sm text-brand-cyan">
            {uiMessage}
          </div>
        ) : null}
        {uiError ? (
          <div className="mt-6 rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {uiError}
          </div>
        ) : null}

        <section className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
          <div className="space-y-6">
            <Card className={cardClass}>
              <CardHeader>
                <CardTitle className="text-white">Marker erfassen</CardTitle>
                <CardDescription className="text-text-muted">
                  Pflichtfelder bleiben schlank: Asset-Typ, Standort per GPS oder manuell und ein Foto direkt vom
                  Geraet.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <label className="space-y-2 text-sm text-text-muted">
                      <span className="block">Asset-Typ</span>
                      <select
                        className="form-select h-11 w-full cursor-pointer rounded-xl border border-border/70 bg-white/5 px-3 text-sm text-white outline-none transition focus:border-brand-cyan/70"
                        value={assetType}
                        onChange={(event) => setAssetType(event.target.value as SiteMarkerAssetType)}
                      >
                        {ASSET_TYPE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value} className="bg-bg text-white">
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="space-y-2 text-sm text-text-muted">
                      <span className="block">Standortquelle</span>
                      <select
                        className="form-select h-11 w-full cursor-pointer rounded-xl border border-border/70 bg-white/5 px-3 text-sm text-white outline-none transition focus:border-brand-cyan/70"
                        value={locationSource}
                        onChange={(event) => setLocationSource(event.target.value as SiteMarkerLocationSource)}
                      >
                        {LOCATION_SOURCE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value} className="bg-bg text-white">
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                      <div>
                        <p className="text-sm font-medium text-white">Koordinate</p>
                        <p className="mt-1 text-xs text-text-dim">
                          GPS setzt die Werte automatisch. Manuelle Eingaben bleiben moeglich und werden lokal
                          vorgehalten.
                        </p>
                      </div>
                      <Button
                        type="button"
                        onClick={handleCaptureGps}
                        disabled={isLocating}
                        className="h-11 w-full rounded-xl bg-brand-cyan px-4 text-slate-950 hover:bg-brand-cyan/90 md:w-auto"
                      >
                        <Crosshair className="mr-2 h-4 w-4" />
                        {isLocating ? "GPS laeuft..." : "GPS uebernehmen"}
                      </Button>
                    </div>
                    <div className="mt-4 grid gap-3 sm:grid-cols-3">
                      <div className="rounded-2xl border border-white/10 bg-black/10 px-3 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Quelle</p>
                        <p className="mt-1 text-sm font-medium text-white">
                          {locationSource === "gps" ? "GPS" : "Manuelle Koordinate"}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-black/10 px-3 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Genauigkeit</p>
                        <p className="mt-1 text-sm font-medium text-white">{formatAccuracy(gpsAccuracyM)}</p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-black/10 px-3 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Letztes GPS</p>
                        <p className="mt-1 text-sm font-medium text-white">
                          {lastLocationAt ? new Date(lastLocationAt).toLocaleTimeString("de-DE") : "Noch nicht gesetzt"}
                        </p>
                      </div>
                    </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      <label className="space-y-2 text-sm text-text-muted">
                        <span className="block">Breitengrad</span>
                        <Input
                          className={fieldClass}
                          type="number"
                          step="0.000001"
                          inputMode="decimal"
                          value={latitude}
                          onChange={(event) => handleCoordinateChange("latitude", event.target.value)}
                          placeholder="z.B. 52.520008"
                        />
                      </label>
                      <label className="space-y-2 text-sm text-text-muted">
                        <span className="block">Laengengrad</span>
                        <Input
                          className={fieldClass}
                          type="number"
                          step="0.000001"
                          inputMode="decimal"
                          value={longitude}
                          onChange={(event) => handleCoordinateChange("longitude", event.target.value)}
                          placeholder="z.B. 13.404954"
                        />
                      </label>
                    </div>
                  </div>

                  <label className="block space-y-2 text-sm text-text-muted">
                    <span className="block">Foto</span>
                    {isNativeShellActive ? (
                      <Button
                        type="button"
                        onClick={handleNativePhotoCapture}
                        disabled={isCapturingNativePhoto}
                        className="mb-3 h-11 w-full rounded-xl border border-brand-cyan/20 bg-brand-cyan/10 text-brand-cyan hover:bg-brand-cyan/15"
                      >
                        <Camera className="mr-2 h-4 w-4" />
                        {isCapturingNativePhoto ? "Kamera startet..." : "Kamera oder Galerie oeffnen"}
                      </Button>
                    ) : null}
                    <input
                      type="file"
                      accept="image/*"
                      capture="environment"
                      onChange={handlePhotoChange}
                      className="block w-full rounded-xl border border-dashed border-border/70 bg-white/5 px-3 py-3 text-sm text-white file:mr-4 file:rounded-lg file:border-0 file:bg-brand-orange file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-brand-orangeHover"
                    />
                    <span className="block text-xs text-text-dim">
                      Mobil wird auf kompatiblen Geraeten direkt die Rueckkamera angeboten. Im nativen Shell steht
                      zusaetzlich der Capacitor-Kameraweg bereit. Erlaubt: JPG, PNG, WEBP bis 10 MB.
                    </span>
                  </label>

                  {photoPreviewUrl ? (
                    <div className="overflow-hidden rounded-2xl border border-white/10 bg-black/10">
                      <img src={photoPreviewUrl} alt="Vorschau der aktuellen Feldaufnahme" className="h-56 w-full object-cover" />
                    </div>
                  ) : null}

                  <Button
                    type="submit"
                    disabled={createMutation.isPending}
                    className="h-12 w-full rounded-xl bg-brand-orange px-5 text-white hover:bg-brand-orangeHover"
                  >
                    {createMutation.isPending ? "Speichert..." : "Marker speichern"}
                  </Button>
                </form>
              </CardContent>
            </Card>

            <Card className={cardClass}>
              <CardHeader>
                <CardTitle className="text-white">Feldkarte</CardTitle>
                <CardDescription className="text-text-muted">
                  Aktuelle Erfassungsposition plus zuletzt synchronisierte Marker fuer schnelle Orientierung auf Handy
                  und Tablet.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="overflow-hidden rounded-[24px] border border-white/10 bg-black/20">
                  <SiteMarkerLeafletMap draftPosition={draftPosition} markers={visibleMarkers} />
                </div>
                <div className="rounded-2xl border border-brand-orange/20 bg-brand-orange/10 px-4 py-3 text-sm text-text-muted">
                  Die Karte dient nur der Dokumentation des realen Standortes und eigener Marker. Sie trifft bewusst
                  keine Aussage zu freier Netzkapazitaet.
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className={cardClass}>
            <CardHeader>
              <CardTitle className="text-white">Eigene Marker</CardTitle>
              <CardDescription className="text-text-muted">
                Jeder Eintrag wird initial als unverified gespeichert und bleibt bewusst ohne automatische
                Netzkapazitaetsaussage.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {listErrorMessage ? (
                <div className="rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
                  Live-Abruf fehlgeschlagen. {hasCachedFallback ? "Es werden zuletzt synchronisierte Marker angezeigt." : listErrorMessage}
                </div>
              ) : null}
              {markersQuery.isLoading ? (
                <div className="rounded-2xl border border-border bg-bg-elev px-4 py-4 text-sm text-text-muted">
                  Lade Marker...
                </div>
              ) : null}
              {!markersQuery.isLoading && visibleMarkers.length === 0 ? (
                <div className="rounded-2xl border border-border bg-bg-elev px-4 py-8 text-center">
                  <p className="text-sm font-medium text-white">Noch keine Vor-Ort-Marker vorhanden.</p>
                  <p className="mt-2 text-sm leading-6 text-text-muted">
                    Starten Sie oben mit dem ersten Asset-Foto und einer belastbaren Standortangabe. Marker bleiben
                    bewusst <span className="font-medium text-white">unverified</span>, bis sie spaeter fachlich
                    eingeordnet oder mit Projekten abgeglichen werden.
                  </p>
                  <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:justify-center">
                    <Link
                      href={primaryContextHref}
                      className="inline-flex h-11 items-center justify-center rounded-xl border border-white/15 bg-white/5 px-4 text-sm font-semibold text-white transition hover:bg-white/10"
                    >
                      {primaryContextLabel}
                    </Link>
                    <Link
                      href="/settings"
                      className="inline-flex h-11 items-center justify-center rounded-xl border border-brand-cyan/20 bg-brand-cyan/10 px-4 text-sm font-semibold text-brand-cyan transition hover:bg-brand-cyan/15"
                    >
                      Tarife & Verlauf
                    </Link>
                  </div>
                </div>
              ) : null}
              {visibleMarkers.map((marker) => (
                <article key={marker.id} className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
                  <img
                    src={getSiteMarkerPhotoUrl(marker.photo_api_path)}
                    alt={`Foto fuer ${formatAssetType(marker.asset_type)}`}
                    className="h-48 w-full object-cover"
                  />
                  <div className="space-y-3 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-medium text-brand-cyan">
                        #{marker.id}
                      </span>
                      <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white">
                        {formatAssetType(marker.asset_type)}
                      </span>
                      <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1 text-xs text-amber-200">
                        {marker.verification_status}
                      </span>
                      {hasCachedFallback ? (
                        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-text-muted">
                          Cache
                        </span>
                      ) : null}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">
                        {formatCoordinate(marker.latitude)}, {formatCoordinate(marker.longitude)}
                      </p>
                      <p className="mt-1 text-xs text-text-muted">
                        Quelle: {marker.location_source === "gps" ? "GPS" : "Manuell"} | Foto: {marker.photo_file_name}
                      </p>
                      <p className="mt-1 text-xs text-text-dim">
                        Erfasst am {new Date(marker.created_at).toLocaleString("de-DE")}
                      </p>
                    </div>
                  </div>
                </article>
              ))}
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}

export default function SiteMarkersPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-bg text-white" />}>
      <SiteMarkersPageContent />
    </Suspense>
  );
}
