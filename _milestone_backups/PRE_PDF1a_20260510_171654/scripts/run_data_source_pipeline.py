from __future__ import annotations

from services.data_source_pipeline import run_data_source_pipeline


def main() -> None:
    snaps = run_data_source_pipeline(["mastr", "smard", "dwd"])
    for s in snaps:
        print(f"{s.name}: {s.validierungsstatus} | records={s.record_count} | hash={s.normalized_hash[:12]}")


if __name__ == "__main__":
    main()

