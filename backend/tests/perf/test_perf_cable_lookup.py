"""Perf-Mikro-Bench für `engine.cable_database.get_cable_params`.

Hintergrund: TIER-1-Perf-Commit hat `lru_cache(maxsize=128)` auf
`get_cable_params` aufgebracht (siehe efdf9aa). Pro Grid-Check wird die
Funktion 3x mit identischen Argumenten aufgerufen (Spannungsfall,
Kurzschluss, Thermik). Dieser Bench liefert eine Baseline für TIER-2-
Diskussionen.

Bewusst klein gehalten — ein Test reicht, mehr Streuung bringt hier nichts.
"""
from __future__ import annotations

import pytest

from engine.cable_database import get_cable_params


@pytest.mark.benchmark(group="cable_lookup")
def test_get_cable_params_hot_path(benchmark) -> None:
    """3 Aufrufe pro Check — identische Args, sollten aus lru_cache kommen."""
    get_cable_params.cache_clear()

    def _three_calls() -> None:
        get_cable_params("aluminum", 150, "medium")
        get_cable_params("aluminum", 150, "medium")
        get_cable_params("aluminum", 150, "medium")

    benchmark(_three_calls)


@pytest.mark.benchmark(group="cable_lookup")
def test_get_cable_params_cold_then_warm(benchmark) -> None:
    """Cache-Clear pro Round, danach 3x — misst Cold-Lookup + 2 Cache-Hits."""

    def _run() -> None:
        get_cable_params.cache_clear()
        get_cable_params("aluminum", 240, "medium")
        get_cable_params("aluminum", 240, "medium")
        get_cable_params("aluminum", 240, "medium")

    benchmark(_run)
