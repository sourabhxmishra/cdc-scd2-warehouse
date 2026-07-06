"""Pipeline orchestrator: read CDC changes past the watermark -> SCD2 MERGE -> advance watermark.

Run one change file at a time so incrementality is visible:

    python data/generate.py
    python -m src.pipeline data/_cdc/day1.csv    # inserts -> 5 current customers
    python -m src.pipeline data/_cdc/day2.csv     # updates -> SCD2 history opens/closes
    python -m src.pipeline data/_cdc/day2.csv     # re-run  -> 0 changes (idempotent)
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from src.cdc_reader import read_changes
from src.scd2 import apply_scd2, current_rows
from src.watermark import Watermark

Row = dict[str, Any]

WAREHOUSE = "warehouse"
DIM_PATH = os.path.join(WAREHOUSE, "dim_customer.json")
WM_PATH = os.path.join(WAREHOUSE, "_watermark.json")


def _load_dim(path: str) -> list[Row]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return []


def _save_dim(path: str, dim: list[Row]) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dim, fh, indent=1)


def run_pipeline(changes_path: str, dim_path: str, wm_path: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Process one change file. Returns a summary dict; advances the watermark on success."""
    watermark = Watermark(wm_path)
    since = watermark.get()
    changes = read_changes(changes_path, since, cfg["lsn_col"])
    dim = _load_dim(dim_path)

    if not changes:
        return {
            "processed": 0,
            "watermark": since,
            "current": len(current_rows(dim, cfg["business_key"])),
            "versions": len(dim),
        }

    new_dim = apply_scd2(dim, changes, cfg["business_key"], cfg["tracked_cols"], cfg["ts_col"])
    max_lsn = max(c[cfg["lsn_col"]] for c in changes)
    _save_dim(dim_path, new_dim)
    watermark.advance(max_lsn)

    return {
        "processed": len(changes),
        "watermark": max_lsn,
        "current": len(current_rows(new_dim, cfg["business_key"])),
        "versions": len(new_dim),
    }


def _print_summary(summary: dict[str, Any], dim_path: str, cfg: dict[str, Any]) -> None:
    print(
        f"processed={summary['processed']}  watermark(LSN)={summary['watermark']}  "
        f"current_customers={summary['current']}  total_versions={summary['versions']}"
    )
    dim = _load_dim(dim_path)
    if not dim:
        return
    print("\ncurrent dim_customer (SCD2, is_current=true):")
    header = [cfg["business_key"], *cfg["tracked_cols"], "valid_from", "valid_to"]
    print("  " + "  ".join(f"{h:<12}" for h in header))
    for row in current_rows(dim, cfg["business_key"]):
        cells = [row.get(h) for h in header]
        print("  " + "  ".join(f"{str(c):<12}" for c in cells))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    from src.config import table_config

    cfg = table_config("customer")
    summary = run_pipeline(argv[1], DIM_PATH, WM_PATH, cfg)
    _print_summary(summary, DIM_PATH, cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
