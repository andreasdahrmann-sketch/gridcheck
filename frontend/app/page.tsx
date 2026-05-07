"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { Header } from "@/components/Header";

const GridCheckForm = dynamic(() => import("@/components/GridCheckForm"), {
  loading: () => <div className="text-sm text-text-muted">Lade Check-Modul...</div>,
});
const NetzbetreiberDashboard = dynamic(() => import("@/components/dashboard/NetzbetreiberDashboard"), {
  loading: () => <div className="text-sm text-text-muted">Lade Dashboard...</div>,
});

export default function Home() {
  const [tab, setTab] = useState<"check" | "dashboard">("check");

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />

      <div className="sticky top-0 z-40 bg-bg/90 backdrop-blur border-b border-border">
        <div className="max-w-6xl mx-auto flex gap-1 p-2">
          <button
            onClick={() => setTab("check")}
            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              tab === "check"
                ? "bg-brand-orange text-white shadow-lg shadow-brand-orange/25"
                : "text-text-muted hover:text-white hover:bg-bg-elev"
            }`}
          >
            ⚡ Netzanschluss-Check
          </button>
          <button
            onClick={() => setTab("dashboard")}
            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              tab === "dashboard"
                ? "bg-brand-mint text-[#05201C] shadow-lg shadow-brand-mint/25"
                : "text-text-muted hover:text-white hover:bg-bg-elev"
            }`}
          >
            📊 Netzbetreiber-Dashboard
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {tab === "check" && <GridCheckForm />}
        {tab === "dashboard" && <NetzbetreiberDashboard />}
      </div>
    </main>
  );
}
