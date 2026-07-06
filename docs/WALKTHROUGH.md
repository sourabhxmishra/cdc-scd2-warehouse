# Walkthrough — reproduce it end-to-end

Everything here runs **locally with no cloud** — the SCD2 engine and watermarking are pure Python,
so the whole incremental load is reproducible on any machine.

## 0. Install

```bash
pip install -r requirements.txt
```

## 1. Generate a synthetic CDC change feed

```bash
python data/generate.py
```

Writes two batches into `data/_cdc/` that stand in for `cdc.fn_cdc_get_all_changes_*`:

- `day1.csv` — 5 inserts (initial load), LSN 1–5
- `day2.csv` — 2 updates (a move + two tier upgrades), 1 new customer, and 1 **duplicate** event, LSN 6–9

## 2. Initial load

```bash
python -m src.pipeline data/_cdc/day1.csv
```

```text
processed=5  watermark(LSN)=5  current_customers=5  total_versions=5
```

Five customers, each an open (current) version with `valid_to = None`.

## 3. Incremental load — SCD2 history opens/closes

```bash
python -m src.pipeline data/_cdc/day2.csv
```

```text
processed=4  watermark(LSN)=9  current_customers=6  total_versions=8

current dim_customer (SCD2, is_current=true):
  cust_key   name    city     tier     valid_from           valid_to
  C-001      Alice   Seattle  Gold     2026-06-01T09:00:00  None
  C-002      Bob     Denver   Gold     2026-06-15T14:00:00  None   <- moved + upgraded
  C-003      Carol   Boston   Bronze   2026-06-01T09:00:00  None
  C-004      Dan     Denver   Silver   2026-06-15T14:05:00  None   <- upgraded (dup collapsed)
  C-005      Eve     Miami    Gold     2026-06-01T09:00:00  None
  C-006      Frank   Chicago  Bronze   2026-06-15T14:00:00  None   <- new customer
```

- **6 current** customers but **8 total versions** — the extra two are the *closed* Austin/C-002
  and Denver-Bronze/C-004 rows (`is_current = false`, with a `valid_to`).
- The duplicate C-004 event (LSN 7 and 9) is **deduped** to one version.

## 4. Prove idempotency

```bash
python -m src.pipeline data/_cdc/day2.csv       # run the exact same file again
```

```text
processed=0  watermark(LSN)=9  current_customers=6  total_versions=8
```

**Zero** rows processed — the watermark is already at LSN 9, so nothing is re-read and nothing
duplicates. Run it as many times as you like; the dimension is unchanged.

## 5. Tests

```bash
ruff check src tests data
pytest -q
```

Covers: insert, update (new version + close old), unchanged no-op, batch idempotency, dedupe
latest-per-key, and a full end-to-end pipeline run.

## 6. Provision the source (optional, cloud)

```bash
az deployment group create -g <rg> -f infra/main.bicep -p sqlAdminPassword=<pwd>
# then, against the 'source' database:
#   sqlcmd -S <fqdn> -d source -i sql/enable_cdc.sql
```

The Bicep provisions an **Azure SQL Standard** database (CDC requires Standard or higher) plus an
**ADLS Gen2** account for the Delta warehouse. Tear it down after capturing screenshots — the repo,
diagram and case study stay live forever.
