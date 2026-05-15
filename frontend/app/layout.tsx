import type { Metadata, Viewport } from "next";
import { Inter_Tight } from "next/font/google";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import { cn } from "@/lib/utils";
import Providers from "./providers";
import { CookieNotice } from "@/components/layout/CookieNotice";
import { SiteFooter } from "@/components/layout/SiteFooter";

const interTight = Inter_Tight({
  subsets: ["latin"],
  variable: "--font-inter-tight",
  weight: ["400", "500", "600", "700", "800", "900"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "GridCheck — Netzanschluss Pre-Check",
  description: "Intelligente Netzanschlussplanung",
  applicationName: "GridCheck",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "GridCheck",
  },
  formatDetection: {
    telephone: false,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#061A1A",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de" className={interTight.variable}>
      <body className={cn("min-h-screen min-h-[100svh] bg-brand-bg font-sans text-brand-textPrimary antialiased")}>
        <Providers>
          <div className="flex min-h-screen min-h-[100svh] flex-col">
            {children}
            <SiteFooter />
            <CookieNotice />
          </div>
        </Providers>
      </body>
    </html>
  );
}
