import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "GridCheck",
    short_name: "GridCheck",
    description: "Installierbare Feld- und Analyseoberflaeche fuer fruehe Netzanschlusspruefungen.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#061A1A",
    theme_color: "#061A1A",
    lang: "de-DE",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
