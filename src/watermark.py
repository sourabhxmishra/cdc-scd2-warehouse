"""High-watermark store — remembers the last processed CDC log sequence number (LSN).

Advancing the watermark only after a successful load is what makes the pipeline
**incremental** (re-reads nothing) and safe to retry.
"""
from __future__ import annotations

import json
import os


class Watermark:
    def __init__(self, path: str) -> None:
        self.path = str(path)

    def get(self) -> int:
        try:
            with open(self.path, encoding="utf-8") as fh:
                return int(json.load(fh).get("lsn", 0))
        except FileNotFoundError:
            return 0

    def advance(self, lsn: int) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"lsn": int(lsn)}, fh)
