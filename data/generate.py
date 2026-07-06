"""Generate a deterministic synthetic CDC change feed for the customer dimension.

    python data/generate.py

Writes two change batches into data/_cdc/ that stand in for `cdc.fn_cdc_get_all_changes_*`:
  - day1.csv : 5 inserts (initial load)
  - day2.csv : 2 updates (a move + two tier upgrades), 1 new customer, and 1 duplicate event
               (same LSN-key emitted twice) so dedupe / idempotency are demonstrable.
"""
from __future__ import annotations

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_cdc")

HEADER = ["lsn", "change_ts", "operation", "cust_key", "name", "city", "tier"]

DAY1 = [
    (1, "2026-06-01T09:00:00", "I", "C-001", "Alice", "Seattle", "Gold"),
    (2, "2026-06-01T09:00:00", "I", "C-002", "Bob", "Austin", "Silver"),
    (3, "2026-06-01T09:00:00", "I", "C-003", "Carol", "Boston", "Bronze"),
    (4, "2026-06-01T09:00:00", "I", "C-004", "Dan", "Denver", "Bronze"),
    (5, "2026-06-01T09:00:00", "I", "C-005", "Eve", "Miami", "Gold"),
]

DAY2 = [
    (6, "2026-06-15T14:00:00", "U", "C-002", "Bob", "Denver", "Gold"),      # moved + upgraded
    (7, "2026-06-15T14:00:00", "U", "C-004", "Dan", "Denver", "Silver"),    # upgraded
    (8, "2026-06-15T14:00:00", "I", "C-006", "Frank", "Chicago", "Bronze"),  # new customer
    (9, "2026-06-15T14:05:00", "U", "C-004", "Dan", "Denver", "Silver"),    # duplicate event
]


def _write(name: str, rows: list[tuple]) -> None:
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        writer.writerows(rows)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    _write("day1.csv", DAY1)
    _write("day2.csv", DAY2)
    print(f"wrote {OUT}\\day1.csv ({len(DAY1)} changes) and day2.csv ({len(DAY2)} changes)")


if __name__ == "__main__":
    main()
