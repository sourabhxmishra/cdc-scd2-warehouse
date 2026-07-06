"""SCD Type 2 engine tests: insert, versioning, idempotency, dedupe."""
from src.scd2 import apply_scd2, current_rows, dedupe_latest, row_hash

BK = "cust_key"
TC = ["name", "city", "tier"]


def _chg(lsn, ts, key, name, city, tier):
    return {
        "lsn": lsn, "change_ts": ts, "cust_key": key,
        "name": name, "city": city, "tier": tier,
    }


def test_insert_new_key_opens_current_version():
    out = apply_scd2([], [_chg(1, "t1", "C-1", "A", "X", "Gold")], BK, TC)
    assert len(out) == 1
    row = out[0]
    assert row["is_current"] is True
    assert row["valid_from"] == "t1"
    assert row["valid_to"] is None
    assert row["city"] == "X"


def test_update_opens_new_version_and_closes_old():
    dim = apply_scd2([], [_chg(1, "t1", "C-1", "A", "X", "Gold")], BK, TC)
    out = apply_scd2(dim, [_chg(2, "t2", "C-1", "A", "Y", "Gold")], BK, TC)  # city X -> Y

    assert len(out) == 2
    current = current_rows(out, BK)
    assert len(current) == 1
    assert current[0]["city"] == "Y"
    assert current[0]["valid_from"] == "t2"

    closed = [r for r in out if not r["is_current"]]
    assert len(closed) == 1
    assert closed[0]["city"] == "X"
    assert closed[0]["valid_to"] == "t2"


def test_no_op_when_tracked_columns_unchanged():
    dim = apply_scd2([], [_chg(1, "t1", "C-1", "A", "X", "Gold")], BK, TC)
    out = apply_scd2(dim, [_chg(2, "t2", "C-1", "A", "X", "Gold")], BK, TC)  # same values
    assert len(out) == 1
    assert current_rows(out, BK)[0]["valid_from"] == "t1"  # untouched


def test_applying_same_batch_twice_is_idempotent():
    changes = [
        _chg(1, "t1", "C-1", "A", "X", "Gold"),
        _chg(2, "t1", "C-2", "B", "Y", "Silver"),
    ]
    once = apply_scd2([], changes, BK, TC)
    twice = apply_scd2(once, changes, BK, TC)
    assert len(twice) == len(once) == 2


def test_dedupe_keeps_latest_change_per_key():
    changes = [
        _chg(1, "t1", "C-1", "A", "X", "Gold"),
        _chg(2, "t2", "C-1", "A", "Z", "Gold"),  # later event for same key
    ]
    out = apply_scd2([], changes, BK, TC)
    current = current_rows(out, BK)
    assert len(current) == 1
    assert current[0]["city"] == "Z"
    assert current[0]["valid_from"] == "t2"


def test_dedupe_latest_direct():
    rows = [
        _chg(1, "t1", "C-1", "A", "X", "Gold"),
        _chg(2, "t2", "C-1", "A", "Z", "Gold"),
        _chg(3, "t1", "C-2", "B", "Y", "Silver"),
    ]
    deduped = {r["cust_key"]: r for r in dedupe_latest(rows, BK)}
    assert len(deduped) == 2
    assert deduped["C-1"]["city"] == "Z"


def test_row_hash_reflects_only_tracked_columns():
    a = _chg(1, "t1", "C-1", "A", "X", "Gold")
    b = _chg(9, "t9", "C-1", "A", "Y", "Gold")  # only city (tracked) differs
    assert row_hash(a, TC) != row_hash(b, TC)
    assert row_hash(a, TC) == row_hash(dict(a), TC)
