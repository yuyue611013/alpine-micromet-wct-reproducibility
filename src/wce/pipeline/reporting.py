"""Non-clobber aggregate writers for the opt-in full pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from wce.contracts.io import require_absent


def write_csv_once(path: str | Path, frame: pd.DataFrame) -> Path:
    target = require_absent(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False)
    return target


def write_parquet_once(path: str | Path, frame: pd.DataFrame) -> Path:
    target = require_absent(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(target, index=False)
    return target


def write_json_once(path: str | Path, payload: Any) -> Path:
    target = require_absent(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return target

