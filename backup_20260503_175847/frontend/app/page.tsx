"use client";

import { useState } from "react";
import { Header } from "@/components/Header";
import GridCheckForm from "@/components/GridCheckForm";
import NetzbetreiberDashboard from "@/components/dashboard/NetzbetreiberDashboard";

export default function Home() {
  const [tab, setTab] = useState<"check" | "dashboard">("check");

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />

      <div className="sticky top-0 z-40 bg-slate-900/95 backdrop-blur border-b border-slate-700">
        <div className="max-w-6xl mx-auto flex gap-1 p-2">
          <button
            onClick={() => setTab("check")}
            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              tab === "check"
                ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                : "text-slate-400 hover:text-white hover:bg-slate-800"
            }`}
          >
            ⚡ Netzanschluss-Check
          </button>
          <button
            onClick={() => setTab("dashboard")}
            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              tab === "dashboard"
                ? "bg-emerald-600 text-white shadow-lg shadow-emerald-600/20"
                : "text-slate-400 hover:text-white hover:bg-slate-800"
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
