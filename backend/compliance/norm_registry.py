"""
Zentrale Norm-Registry - Single Source of Truth fuer alle Normen-Staende.

WICHTIG (Cursor Rule):
- Bei Norm-Update (z.B. neue Fassung VDE-AR-N 4110): NUR hier aendern.
- Jede aenderung erfordert Eintrag in CHANGELOG.md.
- Reports lesen ihre Normen-Liste ausschliesslich aus dieser Datei.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

APP_VERSION_NORMSTAND = "2025-01"


@dataclass(frozen=True)
class Norm:
    norm_id: str
    titel: str
    stand: str
    geltungsbereich: str
    spannungsebenen_kv: tuple[float, float]
    kategorie: str


# === Anwendungsregeln (VDE) ===
VDE_AR_N_4105 = Norm("VDE-AR-N 4105", "Erzeugungsanlagen am Niederspannungsnetz",
    "2018-11", "Erzeugungsanlagen <= 1 kV", (0.0, 1.0), "Anwendungsregel")
VDE_AR_N_4110 = Norm("VDE-AR-N 4110", "Technische Anschlussregeln Mittelspannung",
    "2023-09", "Anschluss > 1 kV bis 35 kV", (1.0, 35.0), "Anwendungsregel")
VDE_AR_N_4120 = Norm("VDE-AR-N 4120", "Technische Anschlussregeln Hochspannung",
    "2017-11+A1:2020-05", "Anschluss > 35 kV bis 110 kV", (35.0, 110.0), "Anwendungsregel")
VDE_AR_N_4130 = Norm("VDE-AR-N 4130", "Technische Anschlussregeln Hoechstspannung",
    "2018-11", "Anschluss > 110 kV", (110.0, 1.0e9), "Anwendungsregel")
VDE_AR_N_4100 = Norm("VDE-AR-N 4100", "Technische Anschlussregeln Niederspannung (TAR NS)",
    "2019-04+A1:2020-05", "Anschlussnehmer Niederspannung", (0.0, 1.0), "Anwendungsregel")
VDE_AR_N_4140 = Norm("VDE-AR-N 4140", "Speicher am Nieder- und Mittelspannungsnetz",
    "2023-08", "Stationaere Batteriespeicher NS/MS", (0.0, 35.0), "Anwendungsregel")
TAB_HOECHSTSPANNUNG_2019 = Norm("TAB Hochspannung 2019", "TransmissionCode / VDN-TAB Hoechstspannung",
    "2019", "Anschluss an Uebertragungsnetz", (110.0, 1.0e9), "Anwendungsregel")

# === EU-Verordnungen ===
EU_2016_631_RFG = Norm("EU 2016/631 (RfG)", "Network Code on Requirements for Generators",
    "2016-04-14", "Erzeugungsanlagen, alle Spannungsebenen (Typ A-D)", (0.0, 1.0e9), "EU-Verordnung")
EU_2016_1388_DCC = Norm("EU 2016/1388 (DCC)", "Demand Connection Code",
    "2016-08-17", "Verbrauchsanlagen, Verteilnetze", (0.0, 1.0e9), "EU-Verordnung")
EU_2016_1447_HVDC = Norm("EU 2016/1447 (HVDC)", "HVDC Connection Code",
    "2016-08-26", "HGUe-Anlagen", (110.0, 1.0e9), "EU-Verordnung")

# === Normen (DIN/IEC/EN) ===
DIN_EN_50160 = Norm("DIN EN 50160", "Merkmale der Spannung in oeffentlichen Elektrizitaetsversorgungsnetzen",
    "2020-11", "Spannungsqualitaet, alle Spannungsebenen", (0.0, 1.0e9), "Norm")
DIN_EN_50549_1 = Norm("DIN EN 50549-1", "Anforderungen an Erzeugungsanlagen NS",
    "2019-12", "Erzeugungsanlagen NS-Anschluss", (0.0, 1.0), "Norm")
DIN_EN_50549_2 = Norm("DIN EN 50549-2", "Anforderungen an Erzeugungsanlagen MS",
    "2019-12", "Erzeugungsanlagen MS-Anschluss", (1.0, 35.0), "Norm")
DIN_EN_60909 = Norm("DIN EN 60909", "Kurzschlussstroeme in Drehstromnetzen",
    "2016-12", "Kurzschlussberechnung", (0.0, 1.0e9), "Norm")
DIN_VDE_0276 = Norm("DIN VDE 0276", "Energiekabel - Strombelastbarkeit",
    "2018-09", "Kabel-Auslegung NS/MS/HS", (0.0, 110.0), "Norm")
DIN_VDE_0100 = Norm("DIN VDE 0100", "Errichten von Niederspannungsanlagen",
    "laufend (Teilreihe)", "NS-Errichtung", (0.0, 1.0), "Norm")

# === Gesetze / Verordnungen ===
ENWG = Norm("EnWG", "Energiewirtschaftsgesetz",
    "2024 (jeweils aktuelle Fassung)", "Rahmenrecht Energieversorgung", (0.0, 1.0e9), "Gesetz")
EEG = Norm("EEG", "Erneuerbare-Energien-Gesetz",
    "2023 (jeweils aktuelle Fassung)", "Foerderung EE-Anlagen", (0.0, 1.0e9), "Gesetz")
NAV = Norm("NAV", "Niederspannungsanschlussverordnung",
    "2008-11 (jeweils aktuelle Fassung)", "NS-Anschluss", (0.0, 1.0), "Gesetz")
KRAFTNAV = Norm("KraftNAV", "Kraftwerks-Netzanschlussverordnung",
    "2007-06 (jeweils aktuelle Fassung)", "Kraftwerksanschluss HS/HoeS", (35.0, 1.0e9), "Gesetz")
GOBD = Norm("GoBD", "Grundsaetze ordnungsmaessiger Buchfuehrung (digital)",
    "2019-11", "Revisionssichere Aufbewahrung", (0.0, 1.0e9), "Gesetz")


NORMEN: dict[str, Norm] = {
    n.norm_id: n for n in [
        VDE_AR_N_4105, VDE_AR_N_4110, VDE_AR_N_4120, VDE_AR_N_4130,
        VDE_AR_N_4100, VDE_AR_N_4140, TAB_HOECHSTSPANNUNG_2019,
        EU_2016_631_RFG, EU_2016_1388_DCC, EU_2016_1447_HVDC,
        DIN_EN_50160, DIN_EN_50549_1, DIN_EN_50549_2,
        DIN_EN_60909, DIN_VDE_0276, DIN_VDE_0100,
        ENWG, EEG, NAV, KRAFTNAV, GOBD,
    ]
}


def get_norm(norm_id: str) -> Optional[Norm]:
    return NORMEN.get(norm_id)


def get_normen_fuer_spannungsebene(
    spannung_kv: float,
    nur_kategorien: Optional[list[str]] = None,
) -> list[Norm]:
    out = []
    for n in NORMEN.values():
        lo, hi = n.spannungsebenen_kv
        if lo <= spannung_kv <= hi:
            if nur_kategorien is None or n.kategorie in nur_kategorien:
                out.append(n)
    return out
