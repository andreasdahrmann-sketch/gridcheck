"""
N-1 Bewertung Mittelspannung (MS)
Version: n1-ms-1.0.0

Stakeholder-faehige Ausgabe:
- Projektierer: klare Entscheidung + Empfehlungen
- Netzbetreiber: technische Begruendung + Normbezug
- Investor/Bank: Konfidenz + Annahmen
- Behoerde/Auditor: Hash, Version, Zeitstempel (revisionssicher)
- KI-Trainer: stabile Feldsemantik, maschinenlesbar
"""

from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json

VERSION = "n1-ms-1.0.0"

# Zentrale Topologie-Definition
TOPOLOGIEN = {
    "stich": {
        "n1_grundsaetzlich": False,
        "max_bewertung": "ROT",
    },
    "stich_mit_notverbindung": {
        "n1_grundsaetzlich": False,
        "max_bewertung": "GELB",
    },
    "ring_offen": {
        "n1_grundsaetzlich": True,
        "max_bewertung": "GRUEN",
    },
    "ring_geschlossen": {
        "n1_grundsaetzlich": True,
        "max_bewertung": "GRUEN",
    },
    "doppelstich": {
        "n1_grundsaetzlich": True,
        "max_bewertung": "GRUEN",
    },
    "vermascht": {
        "n1_grundsaetzlich": True,
        "max_bewertung": "GRUEN",
    },
    "unbekannt": {
        "n1_grundsaetzlich": False,
        "max_bewertung": "ROT",
    },
}


def _f(v, default=0.0):
    try:
        if v is None: return default
        return float(v)
    except (TypeError, ValueError):
        return default

def _hash_eingabe(eingabe: dict) -> str:
    raw = json.dumps(eingabe, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _zeitstempel() -> str:
    return datetime.now(timezone.utc).isoformat()


def bewerte_n1_ms(eingabe: dict) -> dict:
    """
    Erwartete Felder in eingabe (Auszug):
      - topologie: str (siehe TOPOLOGIEN)
      - leistung_mw: float
      - cos_phi: float (default 0.95)
      - restkapazitaet_ms_mva: float | None
      - umschaltzeit_min: float | None
      - redundanz: bool (informativ)
    """

    TOPO_ALIAS = {
        "radial": "stich",
        "ring": "ring_offen",
        "stich": "stich",
        "stich_mit_notverbindung": "stich_mit_notverbindung",
        "ring_offen": "ring_offen",
        "ring_geschlossen": "ring_geschlossen",
        "doppelstich": "doppelstich",
        "vermascht": "vermascht",
        "unbekannt": "unbekannt",
    }
    raw_topo = (eingabe.get("topologie") or "unbekannt").lower().strip()
    topologie = TOPO_ALIAS.get(raw_topo, "unbekannt")
    if topologie not in TOPOLOGIEN:
        topologie = "unbekannt"

    cfg = TOPOLOGIEN[topologie]

    leistung_mw = _f(eingabe.get("leistung_mw"), 0.0)
    cos_phi = _f(eingabe.get("cos_phi"), 0.95) or 0.95
    s_mva = leistung_mw / cos_phi if cos_phi > 0 else float("inf")

    rest = eingabe.get("restkapazitaet_ms_mva", None)
    rest_bekannt = rest is not None
    rest_mva = float(rest) if rest_bekannt else 0.0

    umschaltzeit = eingabe.get("umschaltzeit_min", None)

    annahmen = [
        f"cos phi = {cos_phi} zur Berechnung der Scheinleistung S = P / cos phi",
    ]
    empfehlungen = []
    norm_referenz = ["VDE-AR-N 4110"]

    # Default
    n1_sicher = False
    bewertung = "ROT"
    konfidenz = "mittel"
    begruendung_tech = ""
    begruendung_klartext = ""

    if topologie == "unbekannt":
        bewertung = "ROT"
        n1_sicher = False
        konfidenz = "hoch"
        begruendung_tech = (
            "Topologie unbekannt. Ohne Kenntnis der Netzstruktur ist keine "
            "belastbare N-1-Bewertung moeglich."
        )
        begruendung_klartext = (
            "Wir wissen nicht, wie die Anlage ans Netz angebunden ist. "
            "Daher koennen wir nicht zusichern, dass bei einem Fehler die "
            "Versorgung erhalten bleibt."
        )
        empfehlungen += [
            "Beim Netzbetreiber Topologie und Restkapazitaet erfragen",
            "Bestaetigung der Anschlussart (Stich/Ring/Doppelstich) einholen",
        ]

    elif topologie == "stich":
        bewertung = "ROT"
        n1_sicher = False
        konfidenz = "hoch"
        begruendung_tech = (
            "Stichleitung ohne Notverbindung. Ein Fehler fuehrt zur "
            "vollstaendigen Versorgungsunterbrechung."
        )
        begruendung_klartext = (
            "Bei dieser Anschlussart faellt die Anlage bei einem einzigen "
            "Fehler komplett aus. Ein Netzanschluss ist so meist nicht "
            "genehmigungsfaehig."
        )
        empfehlungen += [
            "Pruefen, ob ein Ring- oder Doppelstichanschluss moeglich ist",
            "Pruefen, ob eine Notverbindung zu einem benachbarten Abgang besteht",
        ]

    elif topologie == "stich_mit_notverbindung":
        # Maximal GELB, niemals GRUEN
        if not rest_bekannt:
            bewertung = "ROT"
            n1_sicher = False
            konfidenz = "hoch"
            begruendung_tech = (
                "Stich mit Notverbindung, aber Restkapazitaet der Notverbindung "
                "unbekannt. Konservativ als 0 angenommen."
            )
            annahmen.append("Restkapazitaet MS unbekannt -> konservativ 0 MVA")
            empfehlungen.append("Restkapazitaet der Notverbindung beim VNB anfragen")
        elif rest_mva + 1e-9 < s_mva:
            bewertung = "ROT"
            n1_sicher = False
            konfidenz = "hoch"
            begruendung_tech = (
                f"Notverbindung trag faehig nur {rest_mva:.2f} MVA, "
                f"benoetigt werden {s_mva:.2f} MVA."
            )
            empfehlungen.append("Leistung reduzieren oder staerkere Notverbindung pruefen")
        else:
            bewertung = "GELB"
            n1_sicher = False  # bewusst False: Umschaltzeit > 0
            konfidenz = "mittel"
            begruendung_tech = (
                "Notverbindung ausreichend dimensioniert, jedoch mit Umschaltzeit. "
                "Kein unterbrechungsfreier (n-0)-Betrieb."
            )
            if umschaltzeit is not None:
                annahmen.append(f"Umschaltzeit ca. {umschaltzeit} min")
            empfehlungen.append(
                "Mit VNB klaeren, ob Umschaltzeit fuer den Anwendungsfall akzeptabel ist"
            )
        begruendung_klartext = (
            "Die Anlage haengt an einer Stichleitung mit Notverbindung. "
            "Bei einem Fehler kann umgeschaltet werden, aber nicht ohne "
            "kurze Unterbrechung."
        )

    else:
        # ring_offen, ring_geschlossen, doppelstich, vermascht — MS screening for all sizes (not only < 2 MW)
        if leistung_mw >= 2.0:
            empfehlungen.append(
                "Großanlage ≥ 2 MW: N-1-/Betriebsmittelreserve mit Netzbetreiber verifizieren "
                "(MVP-Screening maximal N1-2 ohne DSO-Daten)."
            )
            annahmen.append(
                f"Leistung {leistung_mw:.2f} MW in MS — Screening umfasst Topologie und Restkapazität, "
                "keine verbindliche N-1-Zusage."
            )
        if not rest_bekannt:
            # Pre-Check-Logik: N-1-faehige Topologie + fehlende Restkapazitaet
            # -> GELB statt ROT (Konfiguration plausibel, Datenluecke beim VNB schliessen)
            bewertung = "GELB"
            n1_sicher = None
            konfidenz = "mittel"
            begruendung_tech = (
                f"Topologie {topologie} ist grundsaetzlich N-1-faehig. "
                "Restkapazitaet im MS-Netz unbekannt -> finale N-1-Bestaetigung "
                "erfordert VNB-Daten. Pre-Check-Status: bedingt plausibel."
            )
            annahmen.append("Restkapazitaet MS unbekannt -> Pre-Check ohne Netzdaten")
            empfehlungen.append("Restkapazitaet beim VNB anfragen (Netzauskunft)")
        elif rest_mva + 1e-9 < s_mva:
            bewertung = "ROT"
            n1_sicher = False
            konfidenz = "hoch"
            begruendung_tech = (
                f"Topologie {topologie}, aber Restkapazitaet {rest_mva:.2f} MVA "
                f"< benoetigte {s_mva:.2f} MVA."
            )
            empfehlungen += [
                "Leistung reduzieren",
                "Anderen Anschlusspunkt mit hoeherer Restkapazitaet pruefen",
            ]
        else:
            bewertung = "GRUEN"
            n1_sicher = True
            konfidenz = "hoch"
            begruendung_tech = (
                f"Topologie {topologie} ist N-1-faehig. Restkapazitaet "
                f"{rest_mva:.2f} MVA deckt benoetigte {s_mva:.2f} MVA."
            )
        begruendung_klartext = (
            "Die Anschlussart erlaubt grundsaetzlich, dass bei einem Fehler "
            "die Versorgung weiter laeuft. Entscheidend ist, ob im Netz "
            "noch genug Reserve vorhanden ist."
        )

    ergebnis = {
        "topologie": topologie,
        "n1_sicher": n1_sicher,
        "bewertung": bewertung,
        "konfidenz": konfidenz,
        "begruendung_technisch": begruendung_tech,
        "begruendung_klartext": begruendung_klartext,
        "norm_referenz": norm_referenz,
        "annahmen": annahmen,
        "empfehlungen": empfehlungen,
        "kennzahlen": {
            "leistung_mw": leistung_mw,
            "cos_phi": cos_phi,
            "scheinleistung_mva": round(s_mva, 3),
            "restkapazitaet_ms_mva": rest_mva if rest_bekannt else None,
            "restkapazitaet_bekannt": rest_bekannt,
        },
        "berechnungs_version": VERSION,
        "zeitstempel_utc": _zeitstempel(),
        "eingangsdaten_hash": _hash_eingabe(eingabe),
    }
    return ergebnis
