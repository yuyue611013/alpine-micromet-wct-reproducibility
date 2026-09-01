"""Fail-fast validation for the authorized-prepared-input pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from wce.contracts.io import resolve_within
from wce.contracts.scientific import ContractError, validate_station_fold_map


def validate_full_pipeline_config(config: dict[str, Any], input_root: str | Path) -> dict[str, Any]:
    if config.get("scope") != "FULL_PIPELINE_FROM_AUTHORIZED_PREPARED_INPUTS":
        raise ContractError("INVALID_FULL_PIPELINE_SCOPE")
    for flag in ("network_access", "download_data", "external_evaluation", "generate_full_grid", "direct_wct_retraining"):
        if config.get(flag) is not False:
            raise ContractError(f"PROHIBITED_PIPELINE_FLAG:{flag}")
    inputs = config.get("inputs", {})
    required_inputs = {
        "input_contract", "temperature_training_table", "dewpoint_training_table", "wind_training_table",
        "temperature_cell_features", "dewpoint_cell_features", "wind_cell_features", "station_observations",
        "station_fold_map", "elevation_mismatch_map", "station_metadata", "frozen_direct_wct_predictions",
    }
    if not required_inputs.issubset(inputs):
        raise ContractError(f"MISSING_PREPARED_INPUT_KEYS:{sorted(required_inputs - set(inputs))}")
    paths = {name: resolve_within(input_root, value) for name, value in inputs.items()}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise ContractError(f"MISSING_AUTHORIZED_PREPARED_INPUTS:{missing}")
    contract = json.loads(paths["input_contract"].read_text(encoding="utf-8"))
    expected = {
        "ssrd_raw_units_kind": "hourly_accumulated_joule_per_square_metre",
        "ssrd_conversion_divisor": 3600.0,
        "ssrd_conversion_before_feature_derivation": True,
        "station_fold_map_locked": True,
        "four_cell_features": True,
        "contains_full_grid": False,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            raise ContractError(f"PREPARED_INPUT_CONTRACT_FAILED:{key}")
    fold_map = pd.read_csv(paths["station_fold_map"], dtype={"station_id": str})
    fold_map = validate_station_fold_map(fold_map)
    mismatch = pd.read_csv(paths["elevation_mismatch_map"], dtype={"station_id": str})
    if set(mismatch.columns) != {"station_id"} or mismatch.station_id.nunique() != 17:
        raise ContractError("MISMATCH_STATION_CONTRACT_FAILED")
    station_metadata = pd.read_csv(paths["station_metadata"], dtype={"station_id": str})
    metadata_required = {"station_id", "mismatch_group", "elevation_group"}
    if not metadata_required.issubset(station_metadata) or station_metadata.station_id.nunique() != len(fold_map):
        raise ContractError("STATION_METADATA_CONTRACT_FAILED")
    for target, target_config in config.get("targets", {}).items():
        features = target_config.get("features", [])
        if not features or len(features) != len(set(features)):
            raise ContractError(f"FEATURE_LIST_REQUIRED_AND_UNIQUE:{target}")
    return {
        "status": "PASS",
        "scope": config["scope"],
        "station_count": len(fold_map),
        "mismatch_station_count": mismatch.station_id.nunique(),
        "ssrd_contract": "PASS",
        "network_access": False,
        "external_evaluation": False,
        "full_grid_generation": False,
    }
