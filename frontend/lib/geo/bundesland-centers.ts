// Naeherungs-Schwerpunkte der deutschen Bundeslaender.
// Wird zum initialen Zentrieren der Karte benutzt, wenn keine genauere
// Standortinformation vorliegt. Keine amtliche Quelle, kein Anspruch auf
// geometrische Praezision. Nutzer setzt den Marker selbst.

export interface LatLon {
  lat: number;
  lon: number;
}

const CENTERS: Record<string, LatLon> = {
  "Sachsen": { lat: 51.05, lon: 13.45 },
  "Sachsen-Anhalt": { lat: 52.0, lon: 11.7 },
  "Brandenburg": { lat: 52.4, lon: 13.3 },
  "Berlin": { lat: 52.52, lon: 13.4 },
  "Mecklenburg-Vorpommern": { lat: 53.6, lon: 12.7 },
  "Hamburg": { lat: 53.55, lon: 10.0 },
  "Schleswig-Holstein": { lat: 54.2, lon: 9.8 },
  "Niedersachsen": { lat: 52.6, lon: 9.7 },
  "Bremen": { lat: 53.1, lon: 8.8 },
  "Nordrhein-Westfalen": { lat: 51.45, lon: 7.45 },
  "Hessen": { lat: 50.65, lon: 9.0 },
  "Rheinland-Pfalz": { lat: 49.9, lon: 7.45 },
  "Saarland": { lat: 49.4, lon: 7.0 },
  "Baden-Wuerttemberg": { lat: 48.65, lon: 9.35 },
  "Bayern": { lat: 48.95, lon: 11.5 },
  "Thueringen": { lat: 50.9, lon: 11.05 },
};

const GERMANY_CENTER: LatLon = { lat: 51.16, lon: 10.45 };

/**
 * Liefert das Naeherungs-Zentrum fuer das erste passende Bundesland.
 * Faellt bei Unbekanntem auf das Deutschland-Zentrum zurueck.
 */
export function resolveCenter(bundeslaender: readonly string[]): LatLon {
  for (const name of bundeslaender) {
    const hit = CENTERS[name];
    if (hit) return hit;
  }
  return GERMANY_CENTER;
}

export const DEFAULT_CENTER = GERMANY_CENTER;
