type CapacitorCameraResult = {
  dataUrl?: string;
  format?: string;
  webPath?: string;
};

type CapacitorCameraPlugin = {
  getPhoto(options: {
    allowEditing?: boolean;
    correctOrientation?: boolean;
    quality?: number;
    resultType?: "dataUrl" | "uri" | "base64";
    saveToGallery?: boolean;
    source?: "PROMPT" | "CAMERA" | "PHOTOS";
  }): Promise<CapacitorCameraResult>;
};

type CapacitorGeolocationPlugin = {
  getCurrentPosition(options?: {
    enableHighAccuracy?: boolean;
    maximumAge?: number;
    timeout?: number;
  }): Promise<{
    coords: {
      accuracy?: number | null;
      latitude: number;
      longitude: number;
    };
  }>;
};

type CapacitorKeyboardPlugin = {
  setResizeMode?(options: { mode: "body" | "ionic" | "native" | "none" }): Promise<void>;
  setStyle?(options: { style: "DARK" | "LIGHT" }): Promise<void>;
};

type CapacitorStatusBarPlugin = {
  setBackgroundColor?(options: { color: string }): Promise<void>;
  setOverlaysWebView?(options: { overlay: boolean }): Promise<void>;
  setStyle?(options: { style: "DARK" | "LIGHT" }): Promise<void>;
};

type CapacitorRuntime = {
  getPlatform?: () => string;
  isNativePlatform?: () => boolean;
  Plugins?: {
    Camera?: CapacitorCameraPlugin;
    Geolocation?: CapacitorGeolocationPlugin;
    Keyboard?: CapacitorKeyboardPlugin;
    StatusBar?: CapacitorStatusBarPlugin;
  };
};

declare global {
  interface Window {
    Capacitor?: CapacitorRuntime;
  }
}

export {};
