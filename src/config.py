"""Load table definitions (business keys, tracked columns) from config/tables.yaml."""
from __future__ import annotations

from typing import Any

import yaml


def load_tables(path: str = "config/tables.yaml") -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def table_config(name: str, path: str = "config/tables.yaml") -> dict[str, Any]:
    tables = load_tables(path)["tables"]
    for table in tables:
        if table["name"] == name:
            return table
    raise KeyError(f"table {name!r} not found in {path}")
