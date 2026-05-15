"use client";

function readRuntime() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.Capacitor ?? null;
}

function normalizePhotoExtension(format?: string) {
  if (!format) {
    return "jpeg";
  }

  const normalized = format.toLowerCase();
  if (normalized === "jpg") {
    return "jpeg";
  }

  return normalized;
}

async function blobFromPhoto(result: { dataUrl?: string; webPath?: string }) {
  if (result.dataUrl) {
    const response = await fetch(result.dataUrl);
    return response.blob();
  }

  if (result.webPath) {
    const response = await fetch(result.webPath);
    return response.blob();
  }

  throw new Error("Kamerabild wurde nicht bereitgestellt.");
}

export function isNativeShell() {
  return Boolean(readRuntime()?.isNativePlatform?.());
}

export function getNativePlatform() {
  return readRuntime()?.getPlatform?.() ?? "web";
}

export async function applyNativeShellChrome() {
  const runtime = readRuntime();
  if (!runtime?.isNativePlatform?.()) {
    return;
  }

  const statusBar = runtime.Plugins?.StatusBar;
  const keyboard = runtime.Plugins?.Keyboard;

  try {
    await statusBar?.setOverlaysWebView?.({ overlay: false });
    await statusBar?.setBackgroundColor?.({ color: "#061A1A" });
    await statusBar?.setStyle?.({ style: "DARK" });
  } catch {
    // Plattformdetails koennen je nach Emulator/Geraet variieren; Web darf daran nicht scheitern.
  }

  try {
    await keyboard?.setResizeMode?.({ mode: "body" });
    await keyboard?.setStyle?.({ style: "DARK" });
  } catch {
    // Keyboard-Anpassungen sind rein ergonomisch und duerfen den Shell-Start nicht blockieren.
  }
}

export async function captureSiteMarkerPhoto() {
  const runtime = readRuntime();
  if (!runtime?.isNativePlatform?.()) {
    return null;
  }

  const camera = runtime.Plugins?.Camera;
  if (!camera?.getPhoto) {
    return null;
  }

  const photo = await camera.getPhoto({
    allowEditing: false,
    correctOrientation: true,
    quality: 85,
    resultType: "dataUrl",
    saveToGallery: false,
    source: "PROMPT",
  });

  const extension = normalizePhotoExtension(photo.format);
  const blob = await blobFromPhoto(photo);
  const mimeType = blob.type || `image/${extension}`;

  return new File([blob], `site-marker-${Date.now()}.${extension}`, {
    type: mimeType,
    lastModified: Date.now(),
  });
}

export async function getCurrentSiteMarkerPosition(timeoutMs = 10_000) {
  const runtime = readRuntime();
  if (runtime?.isNativePlatform?.() && runtime.Plugins?.Geolocation?.getCurrentPosition) {
    const position = await runtime.Plugins.Geolocation.getCurrentPosition({
      enableHighAccuracy: true,
      maximumAge: 0,
      timeout: timeoutMs,
    });

    return {
      accuracy: position.coords.accuracy ?? null,
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
    };
  }

  if (typeof navigator === "undefined" || !navigator.geolocation) {
    throw new Error("GPS ist in diesem Geraet nicht verfuegbar.");
  }

  return new Promise<{ accuracy: number | null; latitude: number; longitude: number }>((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          accuracy: position.coords.accuracy ?? null,
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        }),
      (error) => reject(new Error(error.message || "GPS-Standort konnte nicht erfasst werden.")),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 0 }
    );
  });
}
