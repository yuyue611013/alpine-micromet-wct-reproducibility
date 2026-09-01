"""Aggregate-only numeric extraction and verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from wce.contracts.scientific import ContractError


def collect_public_numeric_values(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root)
    aggregate = root / "data" / "aggregate"
    component = pd.read_csv(aggregate / "component_metrics_overall_v1.csv").set_index("variable")
    wct = json.loads((aggregate / "wct_primary_metrics_v1.json").read_text(encoding="utf-8"))["metrics"]
    external = pd.read_csv(aggregate / "external_aggregate_metrics_v1.csv").set_index("variable")
    component_names = ["Temperature", "Dew_point_constrained", "U10", "V10", "Wind_speed"]
    external_names = ["Temperature", "Dew_point_constrained", "Wind_speed"]
    return {
        "component_rmse": {
            name: [float(component.loc[name, "background_rmse"]), float(component.loc[name, "corrected_rmse"])]
            for name in component_names
        },
        "primary_wct_rmse": [float(wct["background"]["rmse"]), float(wct["corrected"]["rmse"])],
        "primary_wct_bias": [float(wct["background"]["bias"]), float(wct["corrected"]["bias"])],
        "external_rmse": {
            name: [float(external.loc[name, "background_rmse"]), float(external.loc[name, "corrected_rmse"])]
            for name in external_names
        },
    }


def _rounded(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _rounded(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_rounded(item) for item in value]
    return round(float(value), 3)


def verify_public_numeric_contract(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root)
    config = json.loads((root / "configs" / "public_scientific_config_v1.json").read_text(encoding="utf-8"))
    actual_full_precision = collect_public_numeric_values(root)
    actual_rounded = _rounded(actual_full_precision)
    expected = config["expected_rounded_values"]
    if actual_rounded != expected:
        raise ContractError(f"PUBLIC_NUMERIC_CONTRACT_FAILED:{actual_rounded!r}")
    return {
        "status": "PASS",
        "display_precision": 3,
        "actual_full_precision": actual_full_precision,
        "actual_rounded": actual_rounded,
        "expected_rounded": expected,
        "source": "repository_internal_public_aggregate_files",
    }

