"""Statische Fallback-Werte (Stand 2025, Deutschland)."""

# Strompreis Day-Ahead Spotmarkt (Mittelwert)
FALLBACK_STROMPREIS_EUR_MWH = 85.0

# Netzentgelte EUR/kWh nach Spannungsebene (typische Werte 2025)
NETZENTGELTE_EUR_KWH = {
    "NS": 0.0950,    # Niederspannung
    "MS": 0.0420,    # Mittelspannung
    "HS": 0.0180,    # Hochspannung
    "HoeS": 0.0080,  # Hoechstspannung
}

# EEG-Verguetung EUR/kWh (Volleinspeisung PV, Stand 2025)
EEG_VERGUETUNG_EUR_KWH = {
    "PV_klein": 0.1290,    # bis 100 kWp
    "PV_mittel": 0.1080,   # 100-400 kWp
    "PV_gross": 0.0890,    # 400-1000 kWp
    "PV_freiflaeche": 0.0710,  # ab 1 MWp Freiflaeche
    "Wind_onshore": 0.0735,
}
