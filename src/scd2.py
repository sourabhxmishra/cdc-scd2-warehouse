"""SCD Type 2 merge engine (the heart of the repo).

A pure-Python, dependency-free reference implementation of a Slowly Changing Dimension
**Type 2** upsert. It has the same semantics as the Delta `MERGE` in `sql/merge_scd2.sql`
(close the current version, open a new one) but runs anywhere — so it is unit-tested locally
and in CI without needing Spark or a warehouse.

Guarantees:
- **History**   — every version is kept with `valid_from` / `valid_to` / `is_current`.
- **Idempotent** — a row hash over the tracked columns means re-applying the same change is a
  no-op; the pipeline can run a hundred times and produce the same dimension.
- **Dedupe**    — `dedupe_latest` collapses duplicate / out-of-order change events for a key to
  the latest one before the merge (messy CDC feeds emit duplicates).
"""
from __future__ import annotations

import hashlib
from typing import Any

# SCD2 bookkeeping columns added to every dimension row.
SCD2_COLS = ("valid_from", "valid_to", "is_current", "_hash")

Row = dict[str, Any]


def row_hash(row: Row, tracked_cols: list[str]) -> str:
    """Stable short hash over the tracked (business) columns — detects real changes."""
    payload = "|".join(f"{c}={row.get(c)!r}" for c in tracked_cols)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def dedupe_latest(changes: list[Row], business_key: str, ts_col: str = "change_ts") -> list[Row]:
    """Keep only the latest change per business key (handles duplicate / late events)."""
    latest: dict[Any, Row] = {}
    for c in changes:
        key = c[business_key]
        if key not in latest or c[ts_col] > latest[key][ts_col]:
            latest[key] = c
    # deterministic order for reproducible output / tests
    return [latest[k] for k in sorted(latest)]


def _new_version(change: Row, business_key: str, tracked_cols: list[str],
                 hashed: str, ts_col: str) -> Row:
    version: Row = {business_key: change[business_key]}
    for col in tracked_cols:
        version[col] = change.get(col)
    version["valid_from"] = change[ts_col]
    version["valid_to"] = None
    version["is_current"] = True
    version["_hash"] = hashed
    return version


def apply_scd2(
    dim: list[Row],
    changes: list[Row],
    business_key: str,
    tracked_cols: list[str],
    ts_col: str = "change_ts",
) -> list[Row]:
    """Apply CDC `changes` to dimension `dim` using SCD Type 2 semantics.

    Returns a **new** dimension list (the input is not mutated). For each business key:
    - not present            -> insert the first version (open-ended, current);
    - present, hash changed  -> close the current version (`valid_to`, `is_current=False`) and
      insert a new current version;
    - present, hash unchanged -> no-op (idempotency).
    """
    out: list[Row] = [dict(r) for r in dim]
    current: dict[Any, Row] = {r[business_key]: r for r in out if r.get("is_current")}

    for change in dedupe_latest(changes, business_key, ts_col):
        key = change[business_key]
        hashed = row_hash(change, tracked_cols)
        cur = current.get(key)

        if cur is None:
            version = _new_version(change, business_key, tracked_cols, hashed, ts_col)
            out.append(version)
            current[key] = version
        elif cur["_hash"] != hashed:
            cur["is_current"] = False
            cur["valid_to"] = change[ts_col]
            version = _new_version(change, business_key, tracked_cols, hashed, ts_col)
            out.append(version)
            current[key] = version
        # else: unchanged -> no-op

    return out


def current_rows(dim: list[Row], business_key: str) -> list[Row]:
    """The current (open) version of every business key, ordered by key."""
    rows = [r for r in dim if r.get("is_current")]
    return sorted(rows, key=lambda r: r[business_key])
