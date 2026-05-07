"""Erloesberechnung fuer EE-Anlagen (PV/Wind/BESS)."""
from pricing import get_strompreis_eur_mwh

# Typische Volllaststunden (h/a) - konservative Mittelwerte DE
VOLLLASTSTUNDEN = {
    "PV": 950,
    "WIND_ONSHORE": 2000,
    "WIND_OFFSHORE": 4000,
    "BESS": 400,        # Zyklen-aequivalent (Arbitrage)
    "BIOGAS": 7500,
    "WASSERKRAFT": 4500,
    "DEFAULT": 1000,
}

# EEG-Verguetung 2024/2025 Direktvermarktung Marktpraemie (EUR/MWh) - vereinfacht
EEG_MARKTPRAEMIE_EUR_MWH = {
    "PV": 70.0,         # Freiflaeche < 20 MW
    "WIND_ONSHORE": 73.5,
    "BIOGAS": 165.0,
}

ANLAGENTYP_ALIAS = {
    "PV": "PV",
    "PHOTOVOLTAIK": "PV",
    "WIND": "WIND_ONSHORE",
    "WIND_ONSHORE": "WIND_ONSHORE",
    "WIND_OFFSHORE": "WIND_OFFSHORE",
    "BESS": "BESS",
    "SPEICHER": "BESS",
    "BIOGAS": "BIOGAS",
    "WASSERKRAFT": "WASSERKRAFT",
}


def berechne_erloes(anlagentyp: str, leistung_mw: float,
                    volllaststunden: float = None,
                    nutzungsdauer_jahre: int = 20) -> dict:
    """
    Berechnet jaehrlichen und Lebensdauer-Erloes.
    """
    if leistung_mw <= 0:
        raise ValueError("leistung_mw muss > 0 sein")
    if nutzungsdauer_jahre <= 0:
        raise ValueError("nutzungsdauer_jahre muss > 0 sein")

    raw_typ = (anlagentyp or "DEFAULT").upper()
    typ = ANLAGENTYP_ALIAS.get(raw_typ, raw_typ)
    vlh = volllaststunden if volllaststunden is not None else VOLLLASTSTUNDEN.get(typ, VOLLLASTSTUNDEN["DEFAULT"])

    # Live-Strompreis (SMARD)
    preis_data = get_strompreis_eur_mwh()
    spotpreis = preis_data["price_eur_mwh"]

    # Marktpraemie (falls EEG-faehig)
    marktpraemie = EEG_MARKTPRAEMIE_EUR_MWH.get(typ, 0.0)
    effektiver_preis = max(spotpreis, marktpraemie)  # Marktpraemie sichert Mindesterloes

    # Energie pro Jahr
    energie_mwh_a = leistung_mw * vlh

    # Erloes
    erloes_jahr_eur = energie_mwh_a * effektiver_preis
    erloes_lebensdauer_eur = erloes_jahr_eur * nutzungsdauer_jahre

    return {
        "anlagentyp": typ,
        "leistung_mw": leistung_mw,
        "volllaststunden_h_a": vlh,
        "energie_mwh_a": round(energie_mwh_a, 1),
        "spotpreis_eur_mwh": spotpreis,
        "marktpraemie_eur_mwh": marktpraemie,
        "effektiver_preis_eur_mwh": round(effektiver_preis, 2),
        "erloes_jahr_eur": round(erloes_jahr_eur, 0),
        "erloes_lebensdauer_eur": round(erloes_lebensdauer_eur, 0),
        "nutzungsdauer_jahre": nutzungsdauer_jahre,
        "preis_quelle": preis_data["source"],
        "hinweis": "Bruttoerloes ohne Direktvermarktungs-Abschlag, OPEX und Steuern. Indikativ.",
    }
