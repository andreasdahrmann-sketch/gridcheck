"""Pytest-Konfiguration für Perf-Benchmarks (BL-PERF-006).

Diese Tests laufen NICHT bei `pytest backend/tests/` (ohne Pfad-Filter)
und auch nicht bei einem default `pytest`-Lauf im backend/-Root. Sie sind
Baseline-Benchmarks und gehören in einen separaten Run:

    pytest backend/tests/perf/ --benchmark-only

Die eigentliche Trennung erfolgt zweistufig:
  1) `backend/pytest.ini` enthält `norecursedirs = perf`, damit `pytest`
     ohne Pfad-Filter die Perf-Tests bei der Auto-Discovery überspringt.
  2) Wird das Verzeichnis explizit angegeben (`pytest backend/tests/perf/`),
     greift `norecursedirs` nicht; dieser Conftest skippt die Tests dann nur,
     wenn `--benchmark-only` NICHT gesetzt ist — bzw. ignoriert die Dateien
     ganz, wenn `pytest-benchmark` nicht installiert ist (kein dev-Setup).
"""
from __future__ import annotations

import pytest

try:  # pragma: no cover - optional dev dependency
    import pytest_benchmark  # noqa: F401

    _HAS_PYTEST_BENCHMARK = True
except ImportError:  # pragma: no cover
    _HAS_PYTEST_BENCHMARK = False

collect_ignore_glob: list[str] = []
if not _HAS_PYTEST_BENCHMARK:
    collect_ignore_glob = ["test_perf_*.py"]


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "benchmark: performance baseline benchmark "
        "(run with `pytest backend/tests/perf/ --benchmark-only`)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip perf items, wenn nicht explizit --benchmark-only läuft.

    Auch bei explizitem Pfad sollen die Perf-Tests nicht als normale Tests
    laufen (sonst verfälschen sie reguläre Suiten und das Reporting).
    """
    if not _HAS_PYTEST_BENCHMARK:
        return
    benchmark_only = bool(getattr(config.option, "benchmark_only", False))
    if benchmark_only:
        return
    skip_marker = pytest.mark.skip(
        reason="perf baseline benchmark — explizit mit `--benchmark-only` ausführen"
    )
    for item in items:
        nodeid = item.nodeid.replace("\\", "/")
        if "/tests/perf/" in nodeid or nodeid.startswith("tests/perf/"):
            item.add_marker(skip_marker)
