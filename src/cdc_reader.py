"""CDC reader — returns only change rows past the watermark.

Stands in for `SELECT ... FROM cdc.fn_cdc_get_all_changes_* WHERE __$start_lsn > @watermark`.
Here the change feed is a CSV so the whole pipeline runs locally with no database.
"""
from __future__ import annotations

import csv
from typing import Any

Row = dict[str, Any]


def read_changes(path: str, since_lsn: int, lsn_col: str = "lsn") -> list[Row]:
    """Read the change feed and keep only rows with `lsn > since_lsn`, ordered by LSN."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    changed: list[Row] = []
    for row in rows:
        row[lsn_col] = int(row[lsn_col])
        if row[lsn_col] > since_lsn:
            changed.append(row)

    changed.sort(key=lambda r: r[lsn_col])
    return changed
