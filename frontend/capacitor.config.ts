const serverUrl = process.env.CAPACITOR_SERVER_URL?.trim();
const allowInsecureHttp = process.env.CAPACITOR_ALLOW_INSECURE_HTTP === "1";

function readAllowNavigation(url?: string) {
  if (!url) {
    return undefined;
  }

  try {
    const hostname = new URL(url).hostname;
    return hostname ? [hostname] : undefined;
  } catch {
    return undefined;
  }
}

const config = {
  appId: "de.gridcheck.mobile",
  appName: "GridCheck",
  webDir: "native-shell",
  android: {
    allowMixedContent: allowInsecureHttp,
  },
  ios: {
    contentInset: "automatic",
    preferredContentMode: "mobile",
  },
  plugins: {
    Keyboard: {
      resize: "body",
      resizeOnFullScreen: true,
      style: "DARK",
    },
    StatusBar: {
      backgroundColor: "#FF061A1A",
      overlaysWebView: false,
      style: "DARK",
    },
  },
  ...(serverUrl
    ? {
        server: {
          url: serverUrl,
          cleartext: allowInsecureHttp,
          allowNavigation: readAllowNavigation(serverUrl),
        },
      }
    : {}),
};

export default config;
