"""End-to-end opt-in orchestration from authorized prepared inputs only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from wce.contracts.io import require_absent, resolve_within, sha256_file
from wce.contracts.scientific import ContractError, constrain_dewpoint_same_fold
from wce.pipeline.analysis import (
    component_bootstrap,
    component_metrics_by_groups,
    component_metrics_by_station,
    component_metrics_monthly,
    component_metrics_table,
    direct_wct_comparison,
    primary_wct_table,
    wct_summaries,
)
from wce.pipeline.precheck import validate_full_pipeline_config
from wce.pipeline.prediction import interpolate_columns, predict_cell_residuals, reconstruct_wind_cells
from wce.pipeline.reporting import write_csv_once, write_json_once, write_parquet_once
from wce.pipeline.training import fit_nested_target


def run_full_pipeline(config: dict[str, Any], input_root: str | Path, output_root: str | Path) -> dict[str, Any]:
    """Run no-download/no-grid component OOF analysis from prepared inputs.

    This interface intentionally omits the permission-controlled external endpoint and never
    retrains direct WCT. The output root must not already exist.
    """
    input_base = Path(input_root).resolve()
    output_base = require_absent(Path(output_root).resolve())
    if output_base == input_base or input_base in output_base.parents:
        raise ContractError("OUTPUT_ROOT_MUST_BE_SEPARATE_FROM_INPUT_ROOT")
    precheck = validate_full_pipeline_config(config, input_base)
    output_base.mkdir(parents=True, exist_ok=False)
    inputs = {name: resolve_within(input_base, value) for name, value in config["inputs"].items()}
    fold_map = pd.read_csv(inputs["station_fold_map"], dtype={"station_id": str})
    mismatch = set(pd.read_csv(inputs["elevation_mismatch_map"], dtype={"station_id": str}).station_id.astype(str))
    station_metadata = pd.read_csv(inputs["station_metadata"], dtype={"station_id": str})
    metadata_required = {"station_id", "mismatch_group", "elevation_group"}
    if not metadata_required.issubset(station_metadata) or station_metadata.station_id.duplicated().any():
        raise ContractError("STATION_METADATA_SCHEMA_OR_KEY_FAILED")
    frames = {
        "temperature": pd.read_parquet(inputs["temperature_training_table"]),
        "dewpoint": pd.read_parquet(inputs["dewpoint_training_table"]),
        "ralong": pd.read_parquet(inputs["wind_training_table"]),
        "rcross": pd.read_parquet(inputs["wind_training_table"]),
    }
    models = {}
    for target_name, target_config in config["targets"].items():
        models[target_name] = fit_nested_target(
            frames[target_name], fold_map, mismatch, target_name, target_config["target"], target_config["features"],
            bool(target_config["exclude_mismatch_from_training"]), target_config["lightgbm_params"],
            int(target_config["maximum_inner_rounds"]), int(target_config["early_stopping_rounds"]),
            int(config["training_seed"]), int(config["threads"]), output_base,
        )
    observations = pd.read_parquet(inputs["station_observations"])
    keys = ["station_id", "time_utc", "fold"]
    if observations.duplicated(keys).any():
        raise ContractError("OBSERVATION_KEY_DUPLICATE")
    cell_inputs = {
        "temperature": pd.read_parquet(inputs["temperature_cell_features"]),
        "dewpoint": pd.read_parquet(inputs["dewpoint_cell_features"]),
        "ralong": pd.read_parquet(inputs["wind_cell_features"]),
        "rcross": pd.read_parquet(inputs["wind_cell_features"]),
    }
    predicted_cells = {}
    prediction_columns = {"temperature": "T_predicted_residual", "dewpoint": "Td_predicted_residual", "ralong": "Ralong_predicted_residual", "rcross": "Rcross_predicted_residual"}
    for target_name, target_config in config["targets"].items():
        predicted_cells[target_name] = predict_cell_residuals(
            cell_inputs[target_name], models[target_name], target_config["features"], prediction_columns[target_name], int(config["threads"])
        )
    temperature = interpolate_columns(predicted_cells["temperature"], ["T_background", "T_predicted_residual"])
    temperature["T_corrected"] = temperature.T_background + temperature.T_predicted_residual
    temperature = temperature.merge(observations[keys + ["T_observed"]], on=keys, validate="one_to_one")
    dewpoint = interpolate_columns(predicted_cells["dewpoint"], ["Td_background", "Td_predicted_residual"])
    dewpoint["Td_corrected_unconstrained"] = dewpoint.Td_background + dewpoint.Td_predicted_residual
    dewpoint = dewpoint.merge(observations[keys + ["Td_observed"]], on=keys, validate="one_to_one")
    dewpoint = constrain_dewpoint_same_fold(temperature, dewpoint)
    wind_cells = reconstruct_wind_cells(predicted_cells["ralong"], predicted_cells["rcross"])
    wind = interpolate_columns(wind_cells, ["U10_background", "V10_background", "WindSpeed_background", "U10_corrected", "V10_corrected", "WindSpeed_corrected"])
    wind = wind.merge(observations[keys + ["U10_observed", "V10_observed"]], on=keys, validate="one_to_one")
    wind["WindSpeed_observed"] = np.hypot(wind.U10_observed, wind.V10_observed)
    for name, frame in (("temperature", temperature), ("dewpoint", dewpoint), ("wind", wind)):
        enriched = frame.merge(station_metadata[list(metadata_required)], on="station_id", validate="many_to_one")
        if len(enriched) != len(frame) or enriched[["mismatch_group", "elevation_group"]].isna().any().any():
            raise ContractError(f"STATION_METADATA_JOIN_FAILED:{name}")
        if name == "temperature":
            temperature = enriched
        elif name == "dewpoint":
            dewpoint = enriched
        else:
            wind = enriched
    expected = {
        "temperature": int(config["required_temperature_keys"]),
        "dewpoint": int(config["required_dewpoint_keys"]),
        "wind": int(config["required_wind_keys"]),
    }
    for name, frame in [("temperature", temperature), ("dewpoint", dewpoint), ("wind", wind)]:
        if len(frame) != expected[name] or frame.duplicated(keys).any():
            raise ContractError(f"FINAL_OOF_KEY_CONTRACT_FAILED:{name}")
    write_parquet_once(output_base / "local" / "oof" / "temperature_oof.parquet", temperature)
    write_parquet_once(output_base / "local" / "oof" / "dewpoint_oof.parquet", dewpoint)
    write_parquet_once(output_base / "local" / "oof" / "wind_oof.parquet", wind)
    component_metrics = component_metrics_table(temperature, dewpoint, wind)
    component_monthly = component_metrics_monthly(temperature, dewpoint, wind)
    component_groups = component_metrics_by_groups(temperature, dewpoint, wind)
    component_station = component_metrics_by_station(temperature, dewpoint, wind)
    component_replicates, component_bootstrap_summary = component_bootstrap(
        temperature,
        dewpoint,
        wind,
        int(config["bootstrap_replicates"]),
        int(config["bootstrap_seed"]),
    )
    write_csv_once(output_base / "aggregate" / "component_metrics_overall.csv", component_metrics)
    write_csv_once(output_base / "aggregate" / "component_metrics_monthly.csv", component_monthly)
    write_csv_once(output_base / "aggregate" / "component_metrics_representativeness.csv", component_groups)
    write_csv_once(output_base / "aggregate" / "component_bootstrap_summary.csv", component_bootstrap_summary)
    write_csv_once(output_base / "local" / "station_metrics" / "component_metrics_by_station.csv", component_station)
    write_parquet_once(output_base / "local" / "bootstrap" / "component_bootstrap_replicates.parquet", component_replicates)
    wct = primary_wct_table(temperature, wind)
    wct_primary, wct_secondary = wct_summaries(wct, int(config["bootstrap_replicates"]), int(config["bootstrap_seed"]))
    write_parquet_once(output_base / "local" / "oof" / "primary_wct_rows.parquet", wct)
    write_json_once(output_base / "aggregate" / "wct_primary_metrics.json", wct_primary)
    write_json_once(output_base / "aggregate" / "wct_primary_bootstrap.json", wct_secondary["bootstrap"])
    write_json_once(output_base / "aggregate" / "wct_piecewise_sensitivity.json", wct_secondary["piecewise_sensitivity"])
    frozen = pd.read_parquet(inputs["frozen_direct_wct_predictions"])
    direct_all = direct_wct_comparison(wct, frozen, scenario="all_stations")
    direct_regular = direct_wct_comparison(wct, frozen, scenario="excluding_mismatch", excluded_stations=mismatch)
    direct = pd.concat([direct_all, direct_regular], ignore_index=True)
    write_csv_once(output_base / "aggregate" / "direct_wct_comparison_all_and_mismatch_excluded.csv", direct)
    aggregate_files = sorted((output_base / "aggregate").glob("*"))
    for path in aggregate_files:
        if path.suffix == ".csv":
            columns = set(pd.read_csv(path, nrows=0).columns)
            if {"station_id", "time_utc", "venue_id", "provider_id"} & columns:
                raise ContractError(f"PUBLIC_AGGREGATE_CONTAINS_ROW_KEY:{path.name}")
    numeric_frames = [component_metrics, component_monthly, component_groups, component_bootstrap_summary, direct]
    if any(not np.isfinite(frame.select_dtypes(include=[np.number]).to_numpy(float)).all() for frame in numeric_frames):
        raise ContractError("NONFINITE_PUBLIC_AGGREGATE_OUTPUT")
    validation = {
        "status": "PASS",
        "aggregate_files": [{"relative_path": path.relative_to(output_base).as_posix(), "sha256": sha256_file(path)} for path in aggregate_files],
        "row_level_outputs_confined_to_local": True,
        "restricted_external_output": False,
        "direct_wct_retrained": False,
    }
    write_json_once(output_base / "aggregate" / "public_safe_final_validation.json", validation)
    manifest = {
        "status": "PASS",
        "scope": "FULL_PIPELINE_FROM_AUTHORIZED_PREPARED_INPUTS",
        "precheck": precheck,
        "direct_wct_retrained": False,
        "external_evaluation_run": False,
        "full_grid_generated": False,
        "training_seed": config["training_seed"],
        "bootstrap_replicates": config["bootstrap_replicates"],
        "bootstrap_seed": config["bootstrap_seed"],
        "component_bootstrap": True,
        "monthly_component_metrics": True,
        "representativeness_metrics": True,
        "station_level_metrics_local_only": True,
        "primary_wct_bootstrap": True,
        "piecewise_sensitivity": True,
        "direct_wct_scenarios": ["all_stations", "excluding_mismatch"],
        "public_safe_final_validation": "PASS",
    }
    write_json_once(output_base / "run_manifest.json", manifest)
    return manifest
