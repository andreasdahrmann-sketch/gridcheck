import type { Metadata } from "next";
import { Inter_Tight } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";

const interTight = Inter_Tight({
  subsets: ["latin"],
  variable: "--font-inter-tight",
  weight: ["400", "500", "600", "700", "800", "900"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "GridCheck — Netzanschluss Pre-Check",
  description: "Intelligente Netzanschlussplanung",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de" className={interTight.variable}>
      <body className={cn("bg-brand-bg text-brand-textPrimary font-sans antialiased min-h-screen")}>
        {children}
      </body>
    </html>
  );
}
