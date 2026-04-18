// src/lib/vorbelastung.ts
import { MaStRSummary } from './mastr';

export interface Vorbelastung {
  plz: string;
  installiert_gesamt_kW: number;
  gleichzeitigkeitsfaktor: number;
  geschaetzte_last_kW: number;
  sicherheitsmarge_pct: number;
  effektive_vorbelastung_kW: number;
  trend_warnung: boolean;
  confidence: 'hoch' | 'mittel' | 'niedrig';
  quelle: 'mastr_api' | 'mastr_cache' | 'schaetzung';
  hinweise: string[];
}
const GF: Record<string, number> = { PV: 0.7, Wind: 0.25, Biomasse: 0.85, Speicher: 0.3, Sonstige: 0.5 };
const TRAFO_SIZES = [250, 400, 630, 800, 1000, 1250, 1600];
export function berechneVorbelastung(mastr: MaStRSummary, trafoLeistung_kVA?: number): Vorbelastung {
  const hinweise: string[] = [];
  const geschaetzteLast = mastr.pv_kW * GF.PV + mastr.wind_kW * GF.Wind + mastr.biomasse_kW * GF.Biomasse + mastr.speicher_kW * GF.Speicher + mastr.sonstige_kW * GF.Sonstige;
  const gf = mastr.gesamt_kW > 0 ? geschaetzteLast / mastr.gesamt_kW : 0.5;
  const sicherheit = 15;
  const effektiv = geschaetzteLast * (1 + sicherheit / 100);
  const trendWarnung = mastr.trend_2y_kW > 500;
  if (trendWarnung) hinweise.push('Hoher Zubau: ' + Math.round(mastr.trend_2y_kW) + ' kW in 2 Jahren. Kapazitaet evtl. begrenzt.');
  if (trafoLeistung_kVA) {
    const auslastung = (effektiv / trafoLeistung_kVA) * 100;
    if (auslastung > 80) hinweise.push('Trafo-Auslastung ca. ' + Math.round(auslastung) + '% - Anschluss wahrscheinlich eingeschraenkt.');
    else if (auslastung > 50) hinweise.push('Trafo-Auslastung ca. ' + Math.round(auslastung) + '% - Detailpruefung empfohlen.');
    else hinweise.push('Trafo-Auslastung ca. ' + Math.round(auslastung) + '% - Gute Reserve.');
  } else {
    const est = schaetzeTrafo(mastr.gesamt_kW, mastr.anzahl);
    hinweise.push('Kein Trafo angegeben. Geschaetzt: ' + est + ' kVA');
  }
  let confidence: Vorbelastung['confidence'] = 'niedrig';
  let quelle: Vorbelastung['quelle'] = 'schaetzung';
  if (mastr.anzahl > 50) { confidence = 'hoch'; quelle = 'mastr_api'; }
  else if (mastr.anzahl > 10) { confidence = 'mittel'; quelle = 'mastr_api'; }
  if (mastr.pv_kW > mastr.gesamt_kW * 0.8 && mastr.gesamt_kW > 500) hinweise.push('PV-dominiert (' + Math.round(mastr.pv_kW / mastr.gesamt_kW * 100) + '%). Spannungsanhebung beachten.');
  return { plz: mastr.plz, installiert_gesamt_kW: mastr.gesamt_kW, gleichzeitigkeitsfaktor: Math.round(gf * 100) / 100, geschaetzte_last_kW: Math.round(geschaetzteLast * 10) / 10, sicherheitsmarge_pct: sicherheit, effektive_vorbelastung_kW: Math.round(effektiv * 10) / 10, trend_warnung: trendWarnung, confidence, quelle, hinweise };
}
function schaetzeTrafo(kW: number, n: number): number {
  const est = kW * 0.8 + n * 3;
  for (const t of TRAFO_SIZES) { if (t >= est) return t; }
  return TRAFO_SIZES[TRAFO_SIZES.length - 1];
}
export function getVorbelastungAbzug_kW(v: Vorbelastung): number { return v.effektive_vorbelastung_kW; }
