"""End-to-end pipeline test: watermarked incremental load + SCD2 history + idempotent re-run."""
import csv
import json

from src.pipeline import run_pipeline

CFG = {
    "business_key": "cust_key",
    "tracked_cols": ["name", "city", "tier"],
    "ts_col": "change_ts",
    "lsn_col": "lsn",
}
HEADER = ["lsn", "change_ts", "operation", "cust_key", "name", "city", "tier"]


def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        writer.writerows(rows)


def test_incremental_load_scd2_and_idempotency(tmp_path):
    day1 = str(tmp_path / "day1.csv")
    day2 = str(tmp_path / "day2.csv")
    dim = str(tmp_path / "dim.json")
    wm = str(tmp_path / "wm.json")

    _write(day1, [
        (1, "2026-06-01T09:00:00", "I", "C-001", "Alice", "Seattle", "Gold"),
        (2, "2026-06-01T09:00:00", "I", "C-002", "Bob", "Austin", "Silver"),
    ])
    _write(day2, [
        (3, "2026-06-15T14:00:00", "U", "C-002", "Bob", "Denver", "Gold"),     # moved + upgraded
        (4, "2026-06-15T14:00:00", "I", "C-003", "Carol", "Boston", "Bronze"),  # new
        (5, "2026-06-15T14:00:00", "U", "C-002", "Bob", "Denver", "Gold"),     # duplicate event
    ])

    s1 = run_pipeline(day1, dim, wm, CFG)
    assert (s1["processed"], s1["current"], s1["versions"], s1["watermark"]) == (2, 2, 2, 2)

    s2 = run_pipeline(day2, dim, wm, CFG)
    assert s2["processed"] == 3          # duplicate is read...
    assert s2["current"] == 3            # ...but collapsed: C-001, C-002(v2), C-003
    assert s2["versions"] == 4           # C-002 has 2 versions (1 closed, 1 current)
    assert s2["watermark"] == 5

    # Re-running the same file changes nothing (watermark already advanced).
    s3 = run_pipeline(day2, dim, wm, CFG)
    assert (s3["processed"], s3["current"], s3["versions"]) == (0, 3, 4)

    # C-002 keeps full history.
    data = json.load(open(dim, encoding="utf-8"))
    c2 = [r for r in data if r["cust_key"] == "C-002"]
    assert len(c2) == 2
    closed = next(r for r in c2 if not r["is_current"])
    current = next(r for r in c2 if r["is_current"])
    assert closed["city"] == "Austin"
    assert closed["valid_to"] == "2026-06-15T14:00:00"
    assert current["city"] == "Denver"
    assert current["valid_from"] == "2026-06-15T14:00:00"
    assert current["valid_to"] is None
