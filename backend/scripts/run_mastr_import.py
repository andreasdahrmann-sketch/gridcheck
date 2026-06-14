"""CLI-Smoke-Run fuer MaStR-Import (BL-GIS-003 Skeleton).

Default: --dry-run aktiv (nur lesen + zaehlen, keine DB-Writes).
Per --apply explizit DB-Schreibmodus aktivieren.

Logging via structlog: ConsoleRenderer in dev/test, JSON in staging/prod
(siehe core.logging_setup.configure_logging).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _ensure_backend_root_on_path() -> None:
    here = Path(__file__).resolve()
    backend_root = here.parent.parent
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))


_ensure_backend_root_on_path()

from core.config import settings  # noqa: E402
from core.logging_setup import configure_logging, get_logger  # noqa: E402
from db.database import SessionLocal  # noqa: E402
from services.mastr_import_service import run_mastr_import  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MaStR Import-Skeleton (Smoke-Run gegen lokale CSV).",
    )
    parser.add_argument("--source", required=True, help="Pfad zur CSV-Datei.")
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Default ON: nur lesen und zaehlen. --no-dry-run / --apply schaltet DB-Schreiben ein.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Synonym fuer --no-dry-run: erlaubt DB-Writes.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(app_env=settings.app_env, log_level=settings.log_level)
    logger = get_logger("gridcheck.scripts.run_mastr_import")

    dry_run = args.dry_run and not args.apply
    source_path = Path(args.source)

    logger.info(
        "mastr_smoke_started",
        source=str(source_path),
        dry_run=dry_run,
        app_env=settings.app_env,
    )

    if dry_run:
        run = run_mastr_import(source_path, db_session=None, dry_run=True)  # type: ignore[arg-type]
    else:
        with SessionLocal() as session:
            run = run_mastr_import(source_path, db_session=session, dry_run=False)

    logger.info(
        "mastr_smoke_finished",
        run_id=run.id,
        status=run.status,
        rows_total=run.stats.rows_total,
        rows_inserted=run.stats.rows_inserted,
        rows_updated=run.stats.rows_updated,
        rows_skipped=run.stats.rows_skipped,
        rows_failed=run.stats.rows_failed,
        error_summary=run.error_summary,
    )

    print(
        f"MaStR-Smoke: status={run.status} total={run.stats.rows_total} "
        f"inserted={run.stats.rows_inserted} updated={run.stats.rows_updated} "
        f"skipped={run.stats.rows_skipped} failed={run.stats.rows_failed}"
    )
    return 0 if run.stats.rows_total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
