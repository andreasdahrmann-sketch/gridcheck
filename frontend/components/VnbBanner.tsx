"use client";

import { usePlzLookup } from "@/lib/api/use-plz-lookup";

interface Props {
  plz: string;
}

export default function VnbBanner({ plz }: Props) {
  const status = usePlzLookup(plz);

  if (status.kind === "idle") return null;

  if (status.kind === "loading") {
    return (
      <div className="mt-2 rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-xs text-slate-400">
        VNB-Zuordnung wird gepruft...
      </div>
    );
  }

  if (status.kind === "error") {
    return (
      <div className="mt-2 rounded-lg border border-amber-700/60 bg-amber-900/20 px-3 py-2 text-xs text-amber-200">
        VNB-Zuordnung nicht moeglich: {status.message}
      </div>
    );
  }

  const { data } = status;
  const hasVnb = data.vnb_kandidaten.length > 0;

  return (
    <div className="mt-2 rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-3 text-xs text-slate-300">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-slate-200">
          Zustaendiger Verteilnetzbetreiber (Kandidat):
        </span>

        {hasVnb ? (
          data.vnb_kandidaten.map((v) => (
            <span
              key={v.kuerzel}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-600 bg-slate-800/80 px-2 py-0.5"
            >
              <span className="font-mono text-[11px] text-slate-100">{v.kuerzel}</span>
              <span className="text-slate-400">{v.name}</span>
              {v.snap_verfuegbar && (
                <span className="ml-1 rounded bg-emerald-700/40 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-emerald-200">
                  SNAP
                </span>
              )}
            </span>
          ))
        ) : (
          <span className="text-slate-400">
            Kein Kandidat mit oeffentlichem SNAP-Vorpruefungsportal hinterlegt.
          </span>
        )}

        <span
          className={`ml-auto rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wide ${
            data.snap_verfuegbar
              ? "bg-emerald-700/30 text-emerald-200"
              : "bg-slate-700/50 text-slate-300"
          }`}
        >
          {data.snap_verfuegbar
            ? "SNAP-Vorpruefung verfuegbar"
            : "Keine SNAP-Vorpruefung gelistet"}
        </span>
      </div>

      {data.bundesland_kandidaten.length > 0 && (
        <div className="mt-1.5 text-[11px] text-slate-400">
          Bundesland: {data.bundesland_kandidaten.join(", ")}
        </div>
      )}

      {hasVnb &&
        data.vnb_kandidaten.some((v) => v.snap_url) && (
          <div className="mt-2 flex flex-wrap gap-2">
            {data.vnb_kandidaten
              .filter((v) => v.snap_url)
              .map((v) => (
                <a
                  key={`${v.kuerzel}-link`}
                  href={v.snap_url ?? "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-md border border-blue-700/50 bg-blue-900/20 px-2 py-1 text-[11px] text-blue-200 hover:border-blue-500 hover:text-blue-100"
                >
                  Externe SNAP-Vorpruefung {v.kuerzel} oeffnen &rarr;
                </a>
              ))}
          </div>
        )}

      <div className="mt-2 border-t border-slate-700 pt-2 text-[10px] leading-relaxed text-slate-500">
        Confidence {data.confidence} - Quelle: {data.quelle} - Stand {data.stand}.
        <br />
        {data.hinweis}
        <br />
        <span className="text-amber-200/90">
          TAB des VNB prüfen — Abweichungen von Richtwerten in dieser Vorprüfung sind möglich und üblich.
        </span>
      </div>
    </div>
  );
}
