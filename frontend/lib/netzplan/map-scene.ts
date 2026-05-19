import type { ResolvedProjectLocation } from "@/lib/mapbox/use-project-location";
import type { GridCheckInput, GridCheckResult } from "@/types";

export type NetzplanTone = "good" | "warn" | "critical" | "neutral";

export interface MapPoint {
  lat: number;
  lng: number;
}

export interface NetzplanProjectLocation {
  label: string;
  resolvedLabel: string;
  detail: string;
  source: ResolvedProjectLocation["source"];
  approximate: boolean;
  areaRadiusM: number;
  position: MapPoint;
}

export interface NetzplanMapNode {
  id: string;
  kind: "nap" | "station" | "nvp" | "support" | "bottleneck";
  label: string;
  detail: string;
  tone: NetzplanTone;
  approximate: boolean;
  position: MapPoint;
}

export interface NetzplanMapSegment {
  id: string;
  label: string;
  detail: string;
  tone: NetzplanTone;
  approximate: boolean;
  dashed?: boolean;
  weight?: number;
  points: MapPoint[];
}

export interface NetzplanMapScene {
  center: MapPoint;
  projectLocation: NetzplanProjectLocation;
  nodes: NetzplanMapNode[];
  segments: NetzplanMapSegment[];
}

interface BuildMapSceneArgs {
  input: GridCheckInput;
  result: GridCheckResult;
  projectTitle: string;
  projectLocation: ResolvedProjectLocation;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function formatNumber(value: number, digits = 0): string {
  return new Intl.NumberFormat("de-DE", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

function pickPositive(...values: Array<number | undefined>): number | null {
  for (const value of values) {
    if (typeof value === "number" && Number.isFinite(value) && value > 0) {
      return value;
    }
  }
  return null;
}

function toneFromUtilization(value: number): NetzplanTone {
  if (value >= 100) return "critical";
  if (value >= 80) return "warn";
  if (value > 0) return "good";
  return "neutral";
}

function toneFromRouteRisk(level: GridCheckResult["route_environment"]["risk_level"]): NetzplanTone {
  if (level === "hoch") return "critical";
  if (level === "mittel") return "warn";
  return "good";
}

function toneFromMachbarkeit(stufe: GridCheckResult["machbarkeit_stufe"]): NetzplanTone {
  if (stufe === "gruen") return "good";
  if (stufe === "gelb" || stufe === "orange") return "warn";
  return "critical";
}

function severity(tone: NetzplanTone): number {
  switch (tone) {
    case "critical":
      return 3;
    case "warn":
      return 2;
    case "good":
      return 1;
    default:
      return 0;
  }
}

function strongerTone(left: NetzplanTone, right: NetzplanTone): NetzplanTone {
  return severity(left) >= severity(right) ? left : right;
}

function isRingLikeTopology(topologie: GridCheckInput["topologie"]): boolean {
  return topologie === "ring" || topologie === "ring_offen" || topologie === "ring_geschlossen";
}

function supportsReservePath(topologie: GridCheckInput["topologie"]): boolean {
  return isRingLikeTopology(topologie) || topologie === "doppelstich" || topologie === "vermascht";
}

function reservePathLabel(topologie: GridCheckInput["topologie"]): string {
  if (topologie === "vermascht") return "Vermaschter Nebenast";
  if (topologie === "doppelstich") return "Zweiter Einspeisepfad";
  return "Ring-/Reserveast";
}

function toRadians(value: number): number {
  return (value * Math.PI) / 180;
}

function toDegrees(value: number): number {
  return (value * 180) / Math.PI;
}

function destinationPoint(origin: MapPoint, distanceKm: number, bearingDeg: number): MapPoint {
  const earthRadiusKm = 6371;
  const angularDistance = distanceKm / earthRadiusKm;
  const bearing = toRadians(bearingDeg);
  const lat1 = toRadians(origin.lat);
  const lng1 = toRadians(origin.lng);

  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(angularDistance) +
      Math.cos(lat1) * Math.sin(angularDistance) * Math.cos(bearing),
  );
  const lng2 =
    lng1 +
    Math.atan2(
      Math.sin(bearing) * Math.sin(angularDistance) * Math.cos(lat1),
      Math.cos(angularDistance) - Math.sin(lat1) * Math.sin(lat2),
    );

  return { lat: toDegrees(lat2), lng: toDegrees(lng2) };
}

function midpoint(left: MapPoint, right: MapPoint): MapPoint {
  return {
    lat: (left.lat + right.lat) / 2,
    lng: (left.lng + right.lng) / 2,
  };
}

function curvedPath(start: MapPoint, end: MapPoint, offsetKm: number, bearingDeg: number): MapPoint[] {
  if (offsetKm <= 0) return [start, end];
  const control = destinationPoint(midpoint(start, end), offsetKm, bearingDeg + 90);
  return [start, control, end];
}

function buildNapLabel(input: GridCheckInput, result: GridCheckResult): string {
  const exportKw = pickPositive(
    input.netzanschlusspunkt?.max_export_kw,
    result.projektprofil.max_export_kw,
  );
  const importKw = pickPositive(
    input.netzanschlusspunkt?.max_import_kw,
    result.projektprofil.max_import_kw,
  );

  if (exportKw && importKw) {
    return `NAP ${formatNumber(exportKw, 0)} / ${formatNumber(importKw, 0)} kW`;
  }
  if (exportKw) return `NAP Export ${formatNumber(exportKw, 0)} kW`;
  if (importKw) return `NAP Bezug ${formatNumber(importKw, 0)} kW`;
  return "NAP / Uebergabe";
}

function buildStationLabel(input: GridCheckInput): string {
  if (input.netzanschlusspunkt?.own_substation) return "Eigenes Umspannwerk";
  if (input.netzanschlusspunkt?.own_transformer) return "Eigener Trafo";
  if (input.netzanschlusspunkt?.own_switchgear) return "Eigene Schaltanlage";
  return "Schaltanlage / Trafo";
}

function stableBearingFromPlz(plz: string): number {
  const seed = Number(plz.slice(-2)) || 17;
  return 25 + ((seed * 19) % 285);
}

export function buildNvpCapacityDetail(result: GridCheckResult): string {
  if (result.n1.dso_daten_vorhanden && result.nvp_freie_kapazitaet_kw > 0) {
    return `Vom Netzbetreiber gemeldete Kapazitaetsangabe: ${formatNumber(result.nvp_freie_kapazitaet_kw, 0)} kW`;
  }
  if (result.nvp_freie_kapazitaet_kw > 0) {
    return `Eingabe-/Screeningwert ${formatNumber(result.nvp_freie_kapazitaet_kw, 0)} kW – keine verifizierte freie Netzkapazitaet`;
  }
  return "Keine verifizierte freie Netzkapazitaet; OSM liefert keine Kapazitaetsaussage.";
}

export function buildNetzplanMapScene({
  input,
  result,
  projectTitle,
  projectLocation,
}: BuildMapSceneArgs): NetzplanMapScene {
  const totalDistanceKm = clamp(
    pickPositive(input.entfernung_km, result.nvp_entfernung_km) ?? 4.8,
    1.2,
    35,
  );
  const bearing = stableBearingFromPlz(input.plz);
  const projectTone = toneFromMachbarkeit(result.machbarkeit_stufe);
  const trafoTone = toneFromUtilization(result.trafo_auslastung_pct);
  const lineTone = toneFromUtilization(result.leitung_auslastung_pct);
  const routeTone = toneFromRouteRisk(result.route_environment.risk_level);
  const upstreamTone = strongerTone(lineTone, routeTone);
  const projectPoint = {
    lat: projectLocation.lat,
    lng: projectLocation.lng,
  };

  const nap = destinationPoint(
    projectPoint,
    clamp(totalDistanceKm * 0.18, 0.45, 2.1),
    bearing - 8,
  );
  const station = destinationPoint(
    projectPoint,
    clamp(totalDistanceKm * 0.38, 1.1, Math.max(totalDistanceKm * 0.72, 1.5)),
    bearing + 4,
  );
  const nvp = destinationPoint(projectPoint, totalDistanceKm, bearing + 9);
  const support = destinationPoint(
    station,
    clamp(totalDistanceKm * 0.42, 1.2, 7.5),
    isRingLikeTopology(input.topologie) ? bearing - 75 : bearing + 70,
  );

  const projectNapPath = curvedPath(projectPoint, nap, 0.18, bearing - 12);
  const napStationPath = curvedPath(nap, station, 0.32, bearing + 6);
  const stationNvpPath = curvedPath(
    station,
    nvp,
    clamp(totalDistanceKm * 0.07, 0.35, 2.2),
    isRingLikeTopology(input.topologie) ? bearing - 18 : bearing + 16,
  );
  const supportPath = curvedPath(
    station,
    support,
    clamp(totalDistanceKm * 0.04, 0.2, 0.9),
    bearing - 25,
  );

  const bottleneckCandidates = (
    [
    {
      id: "bottleneck-trafo",
      label: "Trafo-Engpass",
      detail: `${formatNumber(result.trafo_auslastung_pct, 1)} % Auslastung`,
      tone: trafoTone,
      score: severity(trafoTone) * 100 + result.trafo_auslastung_pct,
      position: midpoint(nap, station),
    },
    {
      id: "bottleneck-line",
      label: "Leitungsengpass",
      detail: `${formatNumber(result.leitung_auslastung_pct, 1)} % thermische Auslastung`,
      tone: lineTone,
      score: severity(lineTone) * 100 + result.leitung_auslastung_pct,
      position: midpoint(station, nvp),
    },
    {
      id: "bottleneck-route",
      label: "Trassenrisiko",
      detail:
        result.route_environment.summary ||
        result.route_environment.drivers[0] ||
        "Trassen- und Genehmigungsfaktoren beachten.",
      tone: routeTone,
      score: severity(routeTone) * 100 + result.route_environment.risk_score,
      position: stationNvpPath[Math.min(1, stationNvpPath.length - 1)],
    },
    {
      id: "bottleneck-expansion",
      label: "Ausbaubedarf",
      detail: "Netzausbau oder Auflagen sind im Backend-Ergebnis wahrscheinlich.",
      tone: result.netzausbau_erforderlich ? "critical" : "neutral",
      score: result.netzausbau_erforderlich ? 380 : 0,
      position: midpoint(nvp, station),
    },
    ] satisfies ReadonlyArray<{
      id: string;
      label: string;
      detail: string;
      tone: NetzplanTone;
      score: number;
      position: MapPoint;
    }>
  ).sort((left, right) => right.score - left.score)[0];

  const projectLocationVisual: NetzplanProjectLocation = {
    label: projectTitle,
    resolvedLabel: projectLocation.label,
    detail: projectLocation.detail,
    source: projectLocation.source,
    approximate: projectLocation.approximate,
    areaRadiusM: projectLocation.areaRadiusM,
    position: projectPoint,
  };

  const nodes: NetzplanMapNode[] = [
    {
      id: "nap",
      kind: "nap",
      label: buildNapLabel(input, result),
      detail: "Uebergabepunkt und NAP-Wirkung aus Projektprofil / Backend-Werten.",
      tone: toneFromUtilization(
        Math.max(result.trafo_auslastung_pct, result.leitung_auslastung_pct),
      ),
      approximate: true,
      position: nap,
    },
    {
      id: "station",
      kind: "station",
      label: buildStationLabel(input),
      detail: `Trafo ${formatNumber(result.trafo_auslastung_pct, 1)} % | Leitung ${formatNumber(result.leitung_auslastung_pct, 1)} %`,
      tone: strongerTone(trafoTone, lineTone),
      approximate: true,
      position: station,
    },
    {
      id: "nvp",
      kind: "nvp",
      label: result.nvp_bezeichnung,
      detail: buildNvpCapacityDetail(result),
      tone: upstreamTone,
      approximate: true,
      position: nvp,
    },
  ];

  if (supportsReservePath(input.topologie) || !result.n1_prescreen_ok) {
    nodes.push({
      id: "support",
      kind: "support",
      label: reservePathLabel(input.topologie),
      detail: result.n1_prescreen_ok
        ? "Sekundaerer heuristischer Netzpfad fuer die Topologie-Darstellung."
        : result.n1_prescreen_detail || "N-1-Fall gesondert pruefen.",
      tone: result.n1_prescreen_ok ? "good" : "warn",
      approximate: true,
      position: support,
    });
  }

  if (bottleneckCandidates.score >= 180) {
    nodes.push({
      id: bottleneckCandidates.id,
      kind: "bottleneck",
      label: bottleneckCandidates.label,
      detail: bottleneckCandidates.detail,
      tone: bottleneckCandidates.tone,
      approximate: true,
      position: bottleneckCandidates.position,
    });
  }

  const segments: NetzplanMapSegment[] = [
    {
      id: "project-nap",
      label: "Projektstandort -> NAP",
      detail:
        projectLocation.source === "coordinates"
          ? "Netzstart ab explizit hinterlegter Projektkoordinate."
          : "Netzstart ab bestverfuegbarer Standortaufloesung; Leitungspfad bleibt heuristisch.",
      tone: projectTone,
      approximate: true,
      weight: 6,
      points: projectNapPath,
    },
    {
      id: "nap-station",
      label: "NAP -> Schaltanlage",
      detail: `Uebergangspfad mit Trafo-/Schaltanlagenfokus (${formatNumber(result.trafo_auslastung_pct, 1)} %).`,
      tone: trafoTone,
      approximate: true,
      weight: 8,
      points: napStationPath,
    },
    {
      id: "station-nvp",
      label: "Station -> NVP",
      detail:
        result.route_environment.summary ||
        `Heuristischer Leitungskorridor ueber ca. ${formatNumber(totalDistanceKm, 1)} km.`,
      tone: upstreamTone,
      approximate: true,
      dashed: true,
      weight: 9,
      points: stationNvpPath,
    },
  ];

  if (supportsReservePath(input.topologie) || !result.n1_prescreen_ok) {
    segments.push({
      id: "support-branch",
      label:
        input.topologie === "doppelstich" ? "Zweiter Einspeisepfad" : reservePathLabel(input.topologie),
      detail: result.n1_prescreen_ok
        ? "Sekundaerer Pfad fuer die visuelle Netzstruktur."
        : result.n1_prescreen_detail || "Topologischer Reservepfad zur Pruefung.",
      tone: result.n1_prescreen_ok ? "good" : "warn",
      approximate: true,
      dashed: true,
      weight: 5,
      points: supportPath,
    });
  }

  return {
    center: projectPoint,
    projectLocation: projectLocationVisual,
    nodes,
    segments,
  };
}
