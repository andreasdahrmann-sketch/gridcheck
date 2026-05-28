"""Kabeldaten nach VDE 0276-603 / IEC 60228 fuer Grid-Connection-Screening v2."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal, TypedDict


class CableParameters(TypedDict):
    material: Literal["copper", "aluminum"]
    cross_section: int
    resistance_20: float
    reactance: float
    thermal_limit_a: int
    max_operating_temp: int


CABLE_DATABASE: dict[str, dict[int, CableParameters]] = {
    "copper_underground": {
        16: {"material": "copper", "cross_section": 16, "resistance_20": 1.150, "reactance": 0.075, "thermal_limit_a": 105, "max_operating_temp": 70},
        25: {"material": "copper", "cross_section": 25, "resistance_20": 0.727, "reactance": 0.073, "thermal_limit_a": 135, "max_operating_temp": 70},
        35: {"material": "copper", "cross_section": 35, "resistance_20": 0.524, "reactance": 0.071, "thermal_limit_a": 165, "max_operating_temp": 70},
        50: {"material": "copper", "cross_section": 50, "resistance_20": 0.387, "reactance": 0.069, "thermal_limit_a": 200, "max_operating_temp": 70},
        70: {"material": "copper", "cross_section": 70, "resistance_20": 0.268, "reactance": 0.067, "thermal_limit_a": 245, "max_operating_temp": 70},
        95: {"material": "copper", "cross_section": 95, "resistance_20": 0.193, "reactance": 0.065, "thermal_limit_a": 290, "max_operating_temp": 70},
        120: {"material": "copper", "cross_section": 120, "resistance_20": 0.153, "reactance": 0.064, "thermal_limit_a": 330, "max_operating_temp": 70},
        150: {"material": "copper", "cross_section": 150, "resistance_20": 0.124, "reactance": 0.063, "thermal_limit_a": 370, "max_operating_temp": 70},
        185: {"material": "copper", "cross_section": 185, "resistance_20": 0.099, "reactance": 0.062, "thermal_limit_a": 420, "max_operating_temp": 70},
        240: {"material": "copper", "cross_section": 240, "resistance_20": 0.075, "reactance": 0.060, "thermal_limit_a": 490, "max_operating_temp": 70},
        300: {"material": "copper", "cross_section": 300, "resistance_20": 0.060, "reactance": 0.059, "thermal_limit_a": 560, "max_operating_temp": 70},
    },
    "aluminum_underground": {
        16: {"material": "aluminum", "cross_section": 16, "resistance_20": 1.910, "reactance": 0.075, "thermal_limit_a": 80, "max_operating_temp": 70},
        25: {"material": "aluminum", "cross_section": 25, "resistance_20": 1.200, "reactance": 0.073, "thermal_limit_a": 105, "max_operating_temp": 70},
        35: {"material": "aluminum", "cross_section": 35, "resistance_20": 0.868, "reactance": 0.071, "thermal_limit_a": 130, "max_operating_temp": 70},
        50: {"material": "aluminum", "cross_section": 50, "resistance_20": 0.641, "reactance": 0.069, "thermal_limit_a": 160, "max_operating_temp": 70},
        70: {"material": "aluminum", "cross_section": 70, "resistance_20": 0.443, "reactance": 0.067, "thermal_limit_a": 195, "max_operating_temp": 70},
        95: {"material": "aluminum", "cross_section": 95, "resistance_20": 0.320, "reactance": 0.065, "thermal_limit_a": 230, "max_operating_temp": 70},
        120: {"material": "aluminum", "cross_section": 120, "resistance_20": 0.253, "reactance": 0.064, "thermal_limit_a": 265, "max_operating_temp": 70},
        150: {"material": "aluminum", "cross_section": 150, "resistance_20": 0.206, "reactance": 0.063, "thermal_limit_a": 300, "max_operating_temp": 70},
        185: {"material": "aluminum", "cross_section": 185, "resistance_20": 0.164, "reactance": 0.062, "thermal_limit_a": 340, "max_operating_temp": 70},
        240: {"material": "aluminum", "cross_section": 240, "resistance_20": 0.125, "reactance": 0.060, "thermal_limit_a": 395, "max_operating_temp": 70},
        300: {"material": "aluminum", "cross_section": 300, "resistance_20": 0.100, "reactance": 0.059, "thermal_limit_a": 450, "max_operating_temp": 70},
    },
    "aluminum_mv_underground": {
        50: {"material": "aluminum", "cross_section": 50, "resistance_20": 0.641, "reactance": 0.113, "thermal_limit_a": 185, "max_operating_temp": 90},
        95: {"material": "aluminum", "cross_section": 95, "resistance_20": 0.320, "reactance": 0.109, "thermal_limit_a": 260, "max_operating_temp": 90},
        150: {"material": "aluminum", "cross_section": 150, "resistance_20": 0.206, "reactance": 0.106, "thermal_limit_a": 330, "max_operating_temp": 90},
        185: {"material": "aluminum", "cross_section": 185, "resistance_20": 0.164, "reactance": 0.104, "thermal_limit_a": 370, "max_operating_temp": 90},
        240: {"material": "aluminum", "cross_section": 240, "resistance_20": 0.125, "reactance": 0.101, "thermal_limit_a": 430, "max_operating_temp": 90},
        300: {"material": "aluminum", "cross_section": 300, "resistance_20": 0.100, "reactance": 0.099, "thermal_limit_a": 490, "max_operating_temp": 90},
    },
}

ALPHA_CU = 0.00393
ALPHA_AL = 0.00403


def get_cable_resistance_at_temp(
    r20: float,
    material: Literal["copper", "aluminum"],
    operating_temp_c: float = 70,
) -> float:
    alpha = ALPHA_CU if material == "copper" else ALPHA_AL
    return r20 * (1 + alpha * (operating_temp_c - 20))


@lru_cache(maxsize=128)
def get_cable_params(
    material: Literal["copper", "aluminum"],
    cross_section: int | float,
    voltage_level: Literal["low", "medium"],
) -> CableParameters | None:
    # perf: pro Grid-Check wird die Funktion 3x mit identischen Argumenten
    # aufgerufen (Spannungsfall, Kurzschluss, Thermik); Tabelle ist
    # konstant und das Ergebnis-Dict darf gemeinsam gelesen werden.
    key = f"{material}_mv_underground" if voltage_level == "medium" else f"{material}_underground"
    section = int(round(float(cross_section)))
    table = CABLE_DATABASE.get(key, {})
    if section in table:
        return table[section]
    if not table:
        return None
    nearest = min(table.keys(), key=lambda k: abs(k - section))
    return table[nearest]
