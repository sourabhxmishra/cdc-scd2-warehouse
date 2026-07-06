-- SCD Type 2 upsert as a single idempotent Delta MERGE (Databricks / Fabric / Delta Lake).
-- This is the production form of the logic implemented and unit-tested in src/scd2.py.
--
-- `staged` = the latest change per business key past the watermark, with a `hash` over the
-- tracked columns. The MERGE closes the current version when the hash changes and opens a new
-- one; an unchanged hash is a no-op, so re-running the same batch never duplicates history.

MERGE INTO dim_customer AS t
USING staged AS s
    ON  t.cust_key   = s.cust_key
    AND t.is_current = true

-- Row changed -> close the current version (effective-date it out).
WHEN MATCHED AND t.row_hash <> s.row_hash THEN
    UPDATE SET
        t.is_current = false,
        t.valid_to   = s.change_ts

-- New business key -> open its first version.
WHEN NOT MATCHED THEN
    INSERT (cust_key, name, city, tier, row_hash, valid_from, valid_to, is_current)
    VALUES (s.cust_key, s.name, s.city, s.tier, s.row_hash, s.change_ts, NULL, true);

-- The MATCHED branch only *closes* the old row. Insert the new version for changed keys in a
-- second pass (or a follow-up INSERT ... WHERE), keeping the MERGE single-purpose and idempotent:
INSERT INTO dim_customer (cust_key, name, city, tier, row_hash, valid_from, valid_to, is_current)
SELECT s.cust_key, s.name, s.city, s.tier, s.row_hash, s.change_ts, NULL, true
FROM   staged s
LEFT   JOIN dim_customer t
       ON t.cust_key = s.cust_key AND t.is_current = true AND t.row_hash = s.row_hash
WHERE  t.cust_key IS NULL;   -- no current row already matches this exact version
