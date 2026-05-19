// src/components/dashboard/NetzbetreiberDashboard.tsx
// Netzbetreiber-Dashboard: backendgetriebene Antragsliste mit Priorisierung

"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { listProjects, type Project } from "@/lib/api/projects";
import { priorisiereAntraege, type Antrag, type PrioResult } from "@/lib/priorisierung";
import AntragDetailDrawer from "@/components/dashboard/AntragDetailDrawer";
import type { Anlagentyp, Spannungsebene } from "@/types";
import { cn } from "@/lib/utils";
import { readUserPreferences } from "@/lib/user-preferences";

const TYPEN_LABEL: Record<Anlagentyp, string> = {
  solar: "Solar",
  wind: "Wind",
  batterie: "Batterie",
  waermepumpe: "Waermepumpe",
  ladepark: "Ladepark",
  sonstiges: "Sonstige",
};

const REIFE_LABEL: Record<string, string> = {
  idee: "Idee",
  planung: "Planung",
  genehmigt: "Genehmigt",
  baubereit: "Baubereit",
};

function scoreColor(score: number): string {
  if (score >= 70) return "text-green-400";
  if (score >= 50) return "text-yellow-400";
  if (score >= 30) return "text-orange-400";
  return "text-red-400";
}

function rangBadge(rang: number): string {
  if (rang === 1) return "1";
  if (rang === 2) return "2";
  if (rang === 3) return "3";
  return `#${rang}`;
}

function mapTyp(raw: string | undefined): Anlagentyp {
  switch ((raw ?? "").toLowerCase()) {
    case "solar":
    case "pv":
      return "solar";
    case "wind":
      return "wind";
    case "batterie":
    case "battery":
    case "bess":
      return "batterie";
    case "waermepumpe":
    case "heat_pump":
      return "waermepumpe";
    case "ladepark":
    case "charging":
      return "ladepark";
    default:
      return "sonstiges";
  }
}

function mapSpannung(raw: unknown): Spannungsebene {
  const value = String(raw ?? "MS").toUpperCase();
  if (value === "NS" || value === "HS") return value;
  return "MS";
}

function toAntrag(project: Project): Antrag {
  const roleInputs = project.role_inputs ?? {};
  const roleResults = project.role_results ?? {};
  const stakeholder = roleResults.stakeholder_bewertung;
  const storage = roleInputs.storage_profile;
  const projectProfile = roleResults.projektprofil;
  const routeEnv = roleResults.route_environment;

  return {
    id: `PRJ-${project.id}`,
    antragsteller: roleInputs.antragsteller ?? project.name,
    plz: roleInputs.plz ?? project.plz,
    ort: roleInputs.ort,
    anlagentyp: mapTyp(roleInputs.anlagentyp ?? project.typ),
    leistung_kw: roleInputs.anschlussleistung_kw ?? project.leistung_kw,
    spannungsebene: mapSpannung(roleInputs.spannungsebene),
    eingangsdatum: project.created_at ?? new Date().toISOString().slice(0, 10),
    foerderfrist: roleInputs.foerderfrist,
    baugenehmigung_vorhanden: Boolean(roleInputs.baugenehmigung_vorhanden),
    projektreife: roleInputs.projektreife ?? "idee",
    hat_speicher: Boolean(storage?.has_storage),
    hat_blindleistung: Boolean(storage?.reactive_power_capable),
    hat_einspeisemanagement: Boolean(storage?.dynamic_export_limit || storage?.curtailment_ready),
    gridcheck_score: typeof roleResults.score === "number" ? roleResults.score : undefined,
    storage_operation_mode: storage?.operation_mode,
    stakeholder_konflikt_level: stakeholder?.konflikt_level,
    route_risk_level: routeEnv?.risk_level,
    max_export_kw: projectProfile?.max_export_kw,
    max_import_kw: projectProfile?.max_import_kw,
    remote_control_ready: Boolean(storage?.remote_control_capable),
    netzdienlichkeit_score_backend:
      typeof roleResults.erweiterte_scores?.netzdienlichkeit === "number"
        ? roleResults.erweiterte_scores.netzdienlichkeit
        : undefined,
    stakeholder_fit_score_backend:
      typeof roleResults.erweiterte_scores?.stakeholder_fit === "number"
        ? roleResults.erweiterte_scores.stakeholder_fit
        : undefined,
  };
}

export default function NetzbetreiberDashboard() {
  const [filterTyp, setFilterTyp] = useState<string>("alle");
  const [filterSE, setFilterSE] = useState<string>("alle");
  const [suchtext, setSuchtext] = useState("");
  const [sortBy, setSortBy] = useState<"rang" | "datum" | "leistung">("rang");
  const [selected, setSelected] = useState<{ antrag: Antrag; prio: PrioResult } | null>(null);
  const [compactCards, setCompactCards] = useState(false);

  const projectsQuery = useQuery({
    queryKey: ["projects", "dashboard"],
    queryFn: listProjects,
  });

  useEffect(() => {
    setCompactCards(readUserPreferences().compactProjectCards);
  }, []);

  const antraege = useMemo(() => (projectsQuery.data ?? []).map(toAntrag), [projectsQuery.data]);
  const prioResults = useMemo(() => priorisiereAntraege(antraege), [antraege]);
  const combined = useMemo(
    () =>
      antraege.map((antrag) => ({
        antrag,
        prio: prioResults.find((item) => item.antrag_id === antrag.id) ?? {
          antrag_id: antrag.id,
          rang: 999,
          gesamt_score: 0,
          netzdienlichkeit_score: 0,
          warteliste_score: 0,
          dopplung_erkannt: false,
          dopplung_ids: [],
          dringlichkeit_score: 0,
          hinweise: [],
        },
      })),
    [antraege, prioResults]
  );

  const filtered = useMemo(() => {
    let list = [...combined];
    if (filterTyp !== "alle") list = list.filter((item) => item.antrag.anlagentyp === filterTyp);
    if (filterSE !== "alle") list = list.filter((item) => item.antrag.spannungsebene === filterSE);
    if (suchtext.trim()) {
      const search = suchtext.toLowerCase();
      list = list.filter((item) =>
        item.antrag.id.toLowerCase().includes(search) ||
        item.antrag.antragsteller.toLowerCase().includes(search) ||
        item.antrag.plz.includes(search) ||
        (item.antrag.ort?.toLowerCase().includes(search) ?? false)
      );
    }
    if (sortBy === "rang") list.sort((left, right) => left.prio.rang - right.prio.rang);
    else if (sortBy === "datum") list.sort((left, right) => left.antrag.eingangsdatum.localeCompare(right.antrag.eingangsdatum));
    else list.sort((left, right) => right.antrag.leistung_kw - left.antrag.leistung_kw);
    return list;
  }, [combined, filterTyp, filterSE, suchtext, sortBy]);

  const stats = useMemo(() => {
    const total = antraege.length;
    const dopplungen = prioResults.filter((item) => item.dopplung_erkannt).length;
    const hochPrio = prioResults.filter((item) => item.gesamt_score >= 60 && item.gesamt_score < 80).length;
    const kritisch = prioResults.filter((item) => item.gesamt_score >= 80).length;
    const gesamtMW = antraege.reduce((sum, antrag) => sum + antrag.leistung_kw, 0) / 1000;
    return { total, dopplungen, hochPrio, kritisch, gesamtMW };
  }, [antraege, prioResults]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Netzbetreiber Dashboard</h2>
          <p className="text-sm text-slate-400">
            Backendgetriebene Vorqualifizierung mit Hybrid-, Speicher- und Stakeholder-Kontext
          </p>
        </div>
        <Badge variant="outline" className="w-fit text-xs border-blue-500 text-blue-400">
          {stats.total} Antraege aktiv
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-white">{stats.total}</p>
            <p className="text-xs text-slate-400">Antraege gesamt</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-green-400">{stats.hochPrio}</p>
            <p className="text-xs text-slate-400">Hohe Prioritaet</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-orange-400">{stats.kritisch}</p>
            <p className="text-xs text-slate-400">Dringend</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-red-400">{stats.dopplungen}</p>
            <p className="text-xs text-slate-400">Dopplungen</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-blue-400">{stats.gesamtMW.toFixed(1)} MW</p>
            <p className="text-xs text-slate-400">Gesamtleistung</p>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-slate-800/50 border-slate-700">
        <CardContent className="p-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(0,1.4fr)_160px_130px_150px] xl:items-end">
            <div className="min-w-0">
              <label className="text-xs text-slate-400 mb-1 block">Suche</label>
              <Input
                placeholder="ID, Antragsteller, PLZ, Ort..."
                value={suchtext}
                onChange={e => setSuchtext(e.target.value)}
                className="bg-slate-900 border-slate-600 text-white"
              />
            </div>
            <div className="min-w-0">
              <label className="text-xs text-slate-400 mb-1 block">Anlagentyp</label>
              <Select value={filterTyp} onValueChange={setFilterTyp}>
                <SelectTrigger className="w-full bg-slate-900 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-border bg-bg-card text-white">
                  <SelectItem value="alle">Alle Typen</SelectItem>
                  <SelectItem value="solar">Solar</SelectItem>
                  <SelectItem value="wind">Wind</SelectItem>
                  <SelectItem value="batterie">Batterie</SelectItem>
                  <SelectItem value="waermepumpe">WP</SelectItem>
                  <SelectItem value="ladepark">Ladepark</SelectItem>
                  <SelectItem value="sonstiges">Sonstige</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-0">
              <label className="text-xs text-slate-400 mb-1 block">Spannungsebene</label>
              <Select value={filterSE} onValueChange={setFilterSE}>
                <SelectTrigger className="w-full bg-slate-900 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-border bg-bg-card text-white">
                  <SelectItem value="alle">Alle</SelectItem>
                  <SelectItem value="NS">NS</SelectItem>
                  <SelectItem value="MS">MS</SelectItem>
                  <SelectItem value="HS">HS</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-0">
              <label className="text-xs text-slate-400 mb-1 block">Sortierung</label>
              <Select value={sortBy} onValueChange={(value) => setSortBy(value as "rang" | "datum" | "leistung")}>
                <SelectTrigger className="w-full bg-slate-900 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-border bg-bg-card text-white">
                  <SelectItem value="rang">Prioritaet</SelectItem>
                  <SelectItem value="datum">Eingangsdatum</SelectItem>
                  <SelectItem value="leistung">Leistung</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-3">
        {projectsQuery.isLoading && (
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-8 text-center text-slate-400">Dashboard laedt Projekte...</CardContent>
          </Card>
        )}
        {projectsQuery.isError && (
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-8 text-center text-rose-300">
              Projekte konnten fuer das Dashboard nicht geladen werden.
            </CardContent>
          </Card>
        )}
        {filtered.map(({ antrag: a, prio: p }) => (
          <Card
            key={a.id}
            onClick={() => setSelected({ antrag: a, prio: p })}
            className={`cursor-pointer bg-slate-800/60 border-slate-700 transition-colors hover:border-slate-500 ${
              p.dopplung_erkannt ? "border-l-4 border-l-red-500" : ""
            }`}
          >
            <CardContent className={cn(compactCards ? "p-3" : "p-4")}>
              <div className="flex flex-col gap-4 xl:flex-row xl:items-center">
                <div className="flex items-start gap-3 xl:w-16 xl:flex-col xl:items-center xl:text-center">
                  <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-xl font-bold">
                    {rangBadge(p.rang)}
                  </span>
                  <div className="xl:hidden">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">GridCheck</p>
                    <p className={`text-lg font-bold ${scoreColor(a.gridcheck_score ?? 0)}`}>
                      {a.gridcheck_score ?? "—"}
                    </p>
                  </div>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-sm text-blue-400">{a.id}</span>
                    <Badge variant="outline" className="text-xs">{TYPEN_LABEL[a.anlagentyp]}</Badge>
                    <Badge variant="outline" className="text-xs">{a.spannungsebene}</Badge>
                    {a.hat_speicher && <Badge variant="outline" className="text-xs">Speicher</Badge>}
                    {a.stakeholder_konflikt_level === "hoch" && <Badge variant="destructive" className="text-xs">Zielkonflikt hoch</Badge>}
                    {p.dopplung_erkannt && (
                      <Badge variant="destructive" className="text-xs">Dopplung</Badge>
                    )}
                  </div>
                  <p className="text-white font-medium mt-1">{a.antragsteller}</p>
                  <p className="text-xs text-slate-400">
                    {a.plz} {a.ort} | {a.leistung_kw} kW | {REIFE_LABEL[a.projektreife]} | Eingang: {a.eingangsdatum}
                  </p>
                  {a.foerderfrist && (
                    <p className="text-xs text-orange-400 mt-0.5">Foerderfrist: {a.foerderfrist}</p>
                  )}
                  {(a.max_export_kw || a.max_import_kw) && (
                    <p className="text-xs text-slate-500 mt-1">
                      NAP: Export {a.max_export_kw ?? 0} kW / Bezug {a.max_import_kw ?? 0} kW
                    </p>
                  )}
                </div>

                <div className="w-full rounded-2xl border border-white/10 bg-black/10 p-3 xl:w-[280px] xl:flex-shrink-0">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Gesamt</span>
                    <span className={`font-bold ${scoreColor(p.gesamt_score)}`}>{p.gesamt_score}</span>
                  </div>
                  <Progress value={p.gesamt_score} className="h-2" />

                  <div className="mt-3 grid grid-cols-3 gap-2">
                    <div className="text-center">
                      <p className="text-[10px] text-slate-500">Netzdienl.</p>
                      <p className={`text-xs font-bold ${scoreColor(p.netzdienlichkeit_score)}`}>{p.netzdienlichkeit_score}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-[10px] text-slate-500">Warteliste</p>
                      <p className={`text-xs font-bold ${scoreColor(p.warteliste_score)}`}>{p.warteliste_score}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-[10px] text-slate-500">Dringlichk.</p>
                      <p className={`text-xs font-bold ${scoreColor(p.dringlichkeit_score)}`}>{p.dringlichkeit_score}</p>
                    </div>
                  </div>
                </div>

                <div className="hidden w-16 flex-shrink-0 text-center xl:block">
                  <p className="text-[10px] text-slate-500">GridCheck</p>
                  <p className={`text-lg font-bold ${scoreColor(a.gridcheck_score ?? 0)}`}>{a.gridcheck_score ?? "—"}</p>
                </div>
              </div>

              {p.hinweise.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-700">
                  {p.hinweise.map((h, i) => (
                    <p key={i} className="text-xs text-slate-400">{h}</p>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}

        {filtered.length === 0 && !projectsQuery.isLoading && (
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-8 text-center text-slate-400">
              Keine Antraege gefunden.
            </CardContent>
          </Card>
        )}
      </div>

      <Card className="bg-slate-800/30 border-slate-700">
        <CardContent className="p-4">
          <p className="text-xs text-slate-500 font-medium mb-2">Priorisierungslogik</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-slate-400">
            <div><span className="text-green-400 font-bold">35%</span> Netzdienlichkeit / operative Attraktivitaet</div>
            <div><span className="text-blue-400 font-bold">25%</span> Warteliste (FIFO-Prinzip)</div>
            <div><span className="text-orange-400 font-bold">30%</span> Dringlichkeit / Projektreife</div>
            <div><span className="text-red-400 font-bold">−10%</span> Malus bei erkannter Dopplung</div>
          </div>
        </CardContent>
      </Card>

      <AntragDetailDrawer
        onClose={() => setSelected(null)}
        antrag={selected?.antrag ?? null}
        prio={selected?.prio ?? null}
      />
    </div>
  );
}



