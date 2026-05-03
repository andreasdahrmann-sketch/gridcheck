// src/lib/priorisierung.ts
// Antragspriorisierung: Netzdienlichkeit, Warteliste, Dopplungserkennung, Dringlichkeit

import type { Anlagentyp, Spannungsebene } from '@/types';

// ============================================================
// Types
// ============================================================
export interface Antrag {
  id: string;
  antragsteller: string;
  plz: string;
  ort?: string;
  anlagentyp: Anlagentyp;
  leistung_kw: number;
  spannungsebene: Spannungsebene;
  eingangsdatum: string;           // ISO-Date
  foerderfrist?: string;           // ISO-Date, optional
  baugenehmigung_vorhanden: boolean;
  projektreife: 'idee' | 'planung' | 'genehmigt' | 'baubereit';
  hat_speicher: boolean;
  hat_blindleistung: boolean;
  hat_einspeisemanagement: boolean;
  gridcheck_score?: number;        // aus engine.ts
}

export interface PrioResult {
  antrag_id: string;
  rang: number;
  gesamt_score: number;
  netzdienlichkeit_score: number;
  warteliste_score: number;
  dopplung_erkannt: boolean;
  dopplung_ids: string[];
  dringlichkeit_score: number;
  hinweise: string[];
}

// ============================================================
// Gewichtung (konfigurierbar, Summe = 1.0)
// ============================================================
export const GEWICHTE = {
  netzdienlichkeit: 0.35,
  warteliste: 0.25,
  dringlichkeit: 0.30,
  dopplung_malus: 0.10,   // Abzug bei Dopplung
} as const;

// ============================================================
// 1. Netzdienlichkeit (0-100)
// ============================================================
function bewerteNetzdienlichkeit(a: Antrag): number {
  let score = 0;

  // Anlagentyp-Bonus
  const typBonus: Record<Anlagentyp, number> = {
    batterie: 30,        // Speicher = sehr netzdienlich
    solar: 15,
    wind: 15,
    waermepumpe: 10,     // flexible Last möglich
    ladepark: 10,        // steuerbar
    sonstiges: 5,
  };
  score += typBonus[a.anlagentyp] ?? 5;

  // Speicher-Bonus
  if (a.hat_speicher) score += 25;

  // Blindleistungsfähigkeit
  if (a.hat_blindleistung) score += 15;

  // Einspeisemanagement (§14a EnWG / Redispatch 2.0)
  if (a.hat_einspeisemanagement) score += 15;

  // GridCheck-Score einfließen lassen (Machbarkeit = weniger Netzausbau)
  if (a.gridcheck_score !== undefined) {
    score += Math.round(a.gridcheck_score * 0.15);
  }

  return Math.min(score, 100);
}

// ============================================================
// 2. Warteliste (0-100) - FIFO normiert
// ============================================================
function bewerteWarteliste(a: Antrag, alleDaten: string[]): number {
  if (alleDaten.length <= 1) return 100;

  const sorted = [...alleDaten].sort();
  const idx = sorted.indexOf(a.eingangsdatum);
  // Ältester = 100, Neuester = 0
  return Math.round(((alleDaten.length - 1 - idx) / (alleDaten.length - 1)) * 100);
}

// ============================================================
// 3. Dopplungserkennung
// ============================================================
interface DopplungResult {
  erkannt: boolean;
  ids: string[];
}

function erkenneDopplung(a: Antrag, alle: Antrag[]): DopplungResult {
  const dupes = alle.filter(b =>
    b.id !== a.id &&
    b.plz === a.plz &&
    b.anlagentyp === a.anlagentyp &&
    Math.abs(b.leistung_kw - a.leistung_kw) / Math.max(a.leistung_kw, 1) < 0.15 &&
    b.antragsteller.toLowerCase().trim() === a.antragsteller.toLowerCase().trim()
  );

  return {
    erkannt: dupes.length > 0,
    ids: dupes.map(d => d.id),
  };
}

// ============================================================
// 4. Dringlichkeit (0-100)
// ============================================================
function bewerteDringlichkeit(a: Antrag): number {
  let score = 0;

  // Projektreife
  const reifeScore: Record<string, number> = {
    baubereit: 40,
    genehmigt: 30,
    planung: 15,
    idee: 5,
  };
  score += reifeScore[a.projektreife] ?? 5;

  // Baugenehmigung
  if (a.baugenehmigung_vorhanden) score += 20;

  // Förderfrist-Druck
  if (a.foerderfrist) {
    const tage = Math.round(
      (new Date(a.foerderfrist).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    );
    if (tage < 0) score += 5;           // abgelaufen → niedriger
    else if (tage <= 30) score += 40;    // sehr dringend
    else if (tage <= 90) score += 30;
    else if (tage <= 180) score += 20;
    else score += 10;
  }

  return Math.min(score, 100);
}

// ============================================================
// Gesamtpriorisierung
// ============================================================
export function priorisiereAntraege(antraege: Antrag[]): PrioResult[] {
  if (antraege.length === 0) return [];

  const alleDaten = antraege.map(a => a.eingangsdatum);

  const results: PrioResult[] = antraege.map(a => {
    const nd = bewerteNetzdienlichkeit(a);
    const wl = bewerteWarteliste(a, alleDaten);
    const dr = bewerteDringlichkeit(a);
    const dp = erkenneDopplung(a, antraege);

    const malus = dp.erkannt ? GEWICHTE.dopplung_malus * 100 : 0;

    const gesamt = Math.round(
      nd * GEWICHTE.netzdienlichkeit +
      wl * GEWICHTE.warteliste +
      dr * GEWICHTE.dringlichkeit -
      malus
    );

    const hinweise: string[] = [];
    if (dp.erkannt) hinweise.push(`Mögliche Dopplung mit: ${dp.ids.join(', ')}`);
    if (nd >= 70) hinweise.push('Hohe Netzdienlichkeit → bevorzugte Bearbeitung empfohlen');
    if (dr >= 80) hinweise.push('Hohe Dringlichkeit (Förderfrist / Baubereit)');
    if (wl <= 20) hinweise.push('Neuerer Antrag → niedrigere Wartelistenposition');

    return {
      antrag_id: a.id,
      rang: 0, // wird nach Sortierung gesetzt
      gesamt_score: Math.max(gesamt, 0),
      netzdienlichkeit_score: nd,
      warteliste_score: wl,
      dopplung_erkannt: dp.erkannt,
      dopplung_ids: dp.ids,
      dringlichkeit_score: dr,
      hinweise,
    };
  });

  // Sortierung: höchster Score = Rang 1
  results.sort((a, b) => b.gesamt_score - a.gesamt_score);
  results.forEach((r, i) => r.rang = i + 1);

  return results;
}

// Einzelantrag priorisieren (für Inline-Anzeige im Result)
export function priorisiereEinzel(antrag: Antrag): Omit<PrioResult, 'rang' | 'dopplung_erkannt' | 'dopplung_ids'> {
  const nd = bewerteNetzdienlichkeit(antrag);
  const dr = bewerteDringlichkeit(antrag);

  return {
    antrag_id: antrag.id,
    gesamt_score: Math.round(nd * 0.5 + dr * 0.5),
    netzdienlichkeit_score: nd,
    warteliste_score: 100, // Einzelbetrachtung = kein Vergleich
    dringlichkeit_score: dr,
    hinweise: [],
  };
}

