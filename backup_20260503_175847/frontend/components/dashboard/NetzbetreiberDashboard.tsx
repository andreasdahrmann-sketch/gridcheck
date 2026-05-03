// src/components/dashboard/NetzbetreiberDashboard.tsx
// Netzbetreiber-Dashboard: Antragsliste mit Priorisierung, Dopplungserkennung, Filterfunktion

"use client";

import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { priorisiereAntraege, type Antrag, type PrioResult } from '@/lib/priorisierung';
import AntragDetailDrawer from '@/components/dashboard/AntragDetailDrawer';
import type { Anlagentyp } from '@/types';

// ============================================================
// Demo-Daten (später durch API/DB ersetzt)
// ============================================================
const DEMO_ANTRAEGE: Antrag[] = [
  {
    id: 'ANT-2025-001', antragsteller: 'Solar GmbH', plz: '80331', ort: 'München',
    anlagentyp: 'solar', leistung_kw: 750, spannungsebene: 'MS',
    eingangsdatum: '2025-01-15', foerderfrist: '2025-09-30',
    baugenehmigung_vorhanden: true, projektreife: 'baubereit',
    hat_speicher: true, hat_blindleistung: true, hat_einspeisemanagement: true,
    gridcheck_score: 82,
  },
  {
    id: 'ANT-2025-002', antragsteller: 'Wind Park Nord', plz: '24103', ort: 'Kiel',
    anlagentyp: 'wind', leistung_kw: 3000, spannungsebene: 'MS',
    eingangsdatum: '2025-02-01',
    baugenehmigung_vorhanden: true, projektreife: 'genehmigt',
    hat_speicher: false, hat_blindleistung: true, hat_einspeisemanagement: true,
    gridcheck_score: 68,
  },
  {
    id: 'ANT-2025-003', antragsteller: 'E-Charge AG', plz: '10115', ort: 'Berlin',
    anlagentyp: 'ladepark', leistung_kw: 500, spannungsebene: 'NS',
    eingangsdatum: '2025-03-10', foerderfrist: '2025-06-30',
    baugenehmigung_vorhanden: false, projektreife: 'planung',
    hat_speicher: true, hat_blindleistung: false, hat_einspeisemanagement: false,
    gridcheck_score: 55,
  },
  {
    id: 'ANT-2025-004', antragsteller: 'Batterie Werk Süd', plz: '70173', ort: 'Stuttgart',
    anlagentyp: 'batterie', leistung_kw: 2000, spannungsebene: 'MS',
    eingangsdatum: '2024-11-20',
    baugenehmigung_vorhanden: true, projektreife: 'baubereit',
    hat_speicher: true, hat_blindleistung: true, hat_einspeisemanagement: true,
    gridcheck_score: 91,
  },
  {
    id: 'ANT-2025-005', antragsteller: 'Solar GmbH', plz: '80331', ort: 'München',
    anlagentyp: 'solar', leistung_kw: 780, spannungsebene: 'MS',
    eingangsdatum: '2025-04-01',
    baugenehmigung_vorhanden: false, projektreife: 'idee',
    hat_speicher: false, hat_blindleistung: false, hat_einspeisemanagement: false,
    gridcheck_score: 40,
  },
  {
    id: 'ANT-2025-006', antragsteller: 'WP Service', plz: '50667', ort: 'Köln',
    anlagentyp: 'waermepumpe', leistung_kw: 150, spannungsebene: 'NS',
    eingangsdatum: '2025-03-25',
    baugenehmigung_vorhanden: true, projektreife: 'genehmigt',
    hat_speicher: false, hat_blindleistung: false, hat_einspeisemanagement: true,
    gridcheck_score: 72,
  },
];

// ============================================================
// Helper
// ============================================================
const TYPEN_LABEL: Record<Anlagentyp, string> = {
  solar: '☀️ Solar', wind: '🌬️ Wind', batterie: '🔋 Batterie',
  waermepumpe: '♨️ WP', ladepark: '🔌 Ladepark', sonstiges: '⚡ Sonstige',
};

const REIFE_LABEL: Record<string, string> = {
  idee: '💡 Idee', planung: '📐 Planung', genehmigt: '✅ Genehmigt', baubereit: '🏗️ Baubereit',
};

function scoreColor(score: number): string {
  if (score >= 70) return 'text-green-400';
  if (score >= 50) return 'text-yellow-400';
  if (score >= 30) return 'text-orange-400';
  return 'text-red-400';
}


function rangBadge(rang: number, total: number): string {
  if (rang === 1) return '🥇';
  if (rang === 2) return '🥈';
  if (rang === 3) return '🥉';
  return `#${rang}`;
}

// ============================================================
// Komponente
// ============================================================
export default function NetzbetreiberDashboard() {
  const [filterTyp, setFilterTyp] = useState<string>('alle');
  const [filterSE, setFilterSE] = useState<string>('alle');
  const [suchtext, setSuchtext] = useState('');
  const [sortBy, setSortBy] = useState<'rang' | 'datum' | 'leistung'>('rang');
  const [selected, setSelected] = useState<{ antrag: Antrag; prio: PrioResult } | null>(null);

  // Priorisierung berechnen
  const prioResults = useMemo(() => priorisiereAntraege(DEMO_ANTRAEGE), []);

  // Zusammenführen: Antrag + PrioResult
  const combined = useMemo(() => {
    return DEMO_ANTRAEGE.map(a => ({
      antrag: a,
      prio: prioResults.find(p => p.antrag_id === a.id)!,
    }));
  }, [prioResults]);

  // Filtern
  const filtered = useMemo(() => {
    let list = [...combined];

    if (filterTyp !== 'alle') list = list.filter(c => c.antrag.anlagentyp === filterTyp);
    if (filterSE !== 'alle') list = list.filter(c => c.antrag.spannungsebene === filterSE);
    if (suchtext.trim()) {
      const s = suchtext.toLowerCase();
      list = list.filter(c =>
        c.antrag.id.toLowerCase().includes(s) ||
        c.antrag.antragsteller.toLowerCase().includes(s) ||
        c.antrag.plz.includes(s) ||
        (c.antrag.ort?.toLowerCase().includes(s) ?? false)
      );
    }

    // Sortieren
    if (sortBy === 'rang') list.sort((a, b) => a.prio.rang - b.prio.rang);
    else if (sortBy === 'datum') list.sort((a, b) => a.antrag.eingangsdatum.localeCompare(b.antrag.eingangsdatum));
    else if (sortBy === 'leistung') list.sort((a, b) => b.antrag.leistung_kw - a.antrag.leistung_kw);

    return list;
  }, [combined, filterTyp, filterSE, suchtext, sortBy]);

  // Statistiken
    const stats = useMemo(() => {
    const total = DEMO_ANTRAEGE.length;
    const dopplungen = prioResults.filter(p => p.dopplung_erkannt).length;
    const hochPrio = prioResults.filter(p => p.dringlichkeit_score >= 60 && p.dringlichkeit_score < 80).length;
    const kritisch = prioResults.filter(p => p.dringlichkeit_score >= 80).length;
    const gesamtMW = DEMO_ANTRAEGE.reduce((s, a) => s + a.leistung_kw, 0) / 1000;
    return { total, dopplungen, hochPrio, kritisch, gesamtMW };
  }, [prioResults]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Netzbetreiber Dashboard</h2>
          <p className="text-sm text-slate-400">Antragspriorisierung • Dopplungserkennung • Netzkapazitätsmanagement</p>
        </div>
        <Badge variant="outline" className="text-xs border-blue-500 text-blue-400">
          {stats.total} Anträge aktiv
        </Badge>
      </div>

      {/* KPI-Karten */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-white">{stats.total}</p>
            <p className="text-xs text-slate-400">Anträge gesamt</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-green-400">{stats.hochPrio}</p>
            <p className="text-xs text-slate-400">Hohe Priorität</p>
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

      {/* Filter-Leiste */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="text-xs text-slate-400 mb-1 block">Suche</label>
              <Input
                placeholder="ID, Antragsteller, PLZ, Ort..."
                value={suchtext}
                onChange={e => setSuchtext(e.target.value)}
                className="bg-slate-900 border-slate-600 text-white"
              />
            </div>
            <div className="w-[160px]">
              <label className="text-xs text-slate-400 mb-1 block">Anlagentyp</label>
              <Select value={filterTyp} onValueChange={setFilterTyp}>
                <SelectTrigger className="bg-slate-900 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="alle">Alle Typen</SelectItem>
                  <SelectItem value="solar">☀️ Solar</SelectItem>
                  <SelectItem value="wind">🌬️ Wind</SelectItem>
                  <SelectItem value="batterie">🔋 Batterie</SelectItem>
                  <SelectItem value="waermepumpe">♨️ WP</SelectItem>
                  <SelectItem value="ladepark">🔌 Ladepark</SelectItem>
                  <SelectItem value="sonstiges">⚡ Sonstige</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-[130px]">
              <label className="text-xs text-slate-400 mb-1 block">Spannungsebene</label>
              <Select value={filterSE} onValueChange={setFilterSE}>
                <SelectTrigger className="bg-slate-900 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="alle">Alle</SelectItem>
                  <SelectItem value="NS">NS</SelectItem>
                  <SelectItem value="MS">MS</SelectItem>
                  <SelectItem value="HS">HS</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-[150px]">
              <label className="text-xs text-slate-400 mb-1 block">Sortierung</label>
              <Select value={sortBy} onValueChange={v => setSortBy(v as any)}>
                <SelectTrigger className="bg-slate-900 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="rang">Priorität</SelectItem>
                  <SelectItem value="datum">Eingangsdatum</SelectItem>
                  <SelectItem value="leistung">Leistung</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Antragsliste */}
      <div className="space-y-3">
        {filtered.map(({ antrag: a, prio: p }) => (
          <Card key={a.id} onClick={() => setSelected({ antrag: a, prio: p })} className={`bg-slate-800/60 border-slate-700 hover:border-slate-500 transition-colors cursor-pointer ${p.dopplung_erkannt ? 'border-l-4 border-l-red-500' : ''}`}>
            <CardContent className="p-4">
              <div className="flex flex-col md:flex-row md:items-center gap-4">

                {/* Rang */}
                <div className="flex-shrink-0 w-12 text-center">
                  <span className="text-xl font-bold">{rangBadge(p.rang, filtered.length)}</span>
                </div>

                {/* Hauptinfo */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-sm text-blue-400">{a.id}</span>
                    <Badge variant="outline" className="text-xs">{TYPEN_LABEL[a.anlagentyp]}</Badge>
                    <Badge variant="outline" className="text-xs">{a.spannungsebene}</Badge>
                    {p.dopplung_erkannt && (
                      <Badge variant="destructive" className="text-xs">⚠️ Dopplung</Badge>
                    )}
                  </div>
                  <p className="text-white font-medium mt-1">{a.antragsteller}</p>
                  <p className="text-xs text-slate-400">
                    {a.plz} {a.ort} • {a.leistung_kw} kW • {REIFE_LABEL[a.projektreife]} • Eingang: {a.eingangsdatum}
                  </p>
                  {a.foerderfrist && (
                    <p className="text-xs text-orange-400 mt-0.5">⏰ Förderfrist: {a.foerderfrist}</p>
                  )}
                </div>

                {/* Scores */}
                <div className="flex-shrink-0 w-[280px] space-y-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Gesamt</span>
                    <span className={`font-bold ${scoreColor(p.gesamt_score)}`}>{p.gesamt_score}</span>
                  </div>
                  <Progress value={p.gesamt_score} className="h-2" />

                  <div className="grid grid-cols-3 gap-2 mt-2">
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

                {/* GridCheck Score */}
                <div className="flex-shrink-0 text-center w-16">
                  <p className="text-[10px] text-slate-500">GridCheck</p>
                  <p className={`text-lg font-bold ${scoreColor(a.gridcheck_score ?? 0)}`}>
                    {a.gridcheck_score ?? '—'}
                  </p>
                </div>
              </div>

              {/* Hinweise */}
              {p.hinweise.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-700">
                  {p.hinweise.map((h, i) => (
                    <p key={i} className="text-xs text-slate-400">💡 {h}</p>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}

        {filtered.length === 0 && (
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-8 text-center text-slate-400">
              Keine Anträge gefunden.
            </CardContent>
          </Card>
        )}
      </div>

      {/* Legende */}
      <Card className="bg-slate-800/30 border-slate-700">
        <CardContent className="p-4">
          <p className="text-xs text-slate-500 font-medium mb-2">Priorisierungslogik</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-slate-400">
            <div><span className="text-green-400 font-bold">35%</span> Netzdienlichkeit (Speicher, Blindleistung, Typ)</div>
            <div><span className="text-blue-400 font-bold">25%</span> Warteliste (FIFO-Prinzip)</div>
            <div><span className="text-orange-400 font-bold">30%</span> Dringlichkeit (Projektreife, Förderfrist)</div>
            <div><span className="text-red-400 font-bold">−10%</span> Malus bei erkannter Dopplung</div>
          </div>
        </CardContent>
      </Card>

      <AntragDetailDrawer
        open={selected !== null}
        onClose={() => setSelected(null)}
        antrag={selected?.antrag ?? null}
        prio={selected?.prio ?? null}
      />
    </div>
  );
}


