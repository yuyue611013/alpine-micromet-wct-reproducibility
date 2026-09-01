"""Prepared four-cell feature prediction and station interpolation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from wce.contracts.scientific import ContractError, reconstruct_wind


CELL_KEYS = ["station_id", "time_utc", "fold", "cell_index"]
STATION_KEYS = ["station_id", "time_utc", "fold"]


def predict_cell_residuals(
    cell_frame: pd.DataFrame,
    model_paths: dict[int, Path],
    feature_columns: list[str],
    result_column: str,
    threads: int,
) -> pd.DataFrame:
    try:
        import lightgbm as lgb
    except ImportError as exc:
        raise ContractError("LIGHTGBM_REQUIRED_FOR_FULL_PIPELINE") from exc
    required = set(CELL_KEYS + ["weight", *feature_columns])
    if not required.issubset(cell_frame):
        raise ContractError(f"CELL_FEATURE_SCHEMA_MISSING:{sorted(required - set(cell_frame.columns))}")
    if cell_frame.duplicated(CELL_KEYS).any():
        raise ContractError("DUPLICATE_STATION_CELL_KEY")
    counts = cell_frame.groupby(STATION_KEYS).size()
    weight_sums = cell_frame.groupby(STATION_KEYS).weight.sum()
    if not counts.eq(4).all() or not np.allclose(weight_sums, 1.0, rtol=0, atol=1e-12):
        raise ContractError("FOUR_CELL_COUNT_OR_WEIGHT_CONTRACT_FAILED")
    result = cell_frame.copy()
    result[result_column] = np.nan
    for fold in range(5):
        mask = result.fold.astype(int).eq(fold)
        if not mask.any() or fold not in model_paths:
            raise ContractError(f"MISSING_FOLD_MODEL_OR_FEATURES:{fold}")
        booster = lgb.Booster(model_file=str(model_paths[fold]))
        result.loc[mask, result_column] = booster.predict(result.loc[mask, feature_columns], num_threads=int(threads))
    if not np.isfinite(result[result_column]).all():
        raise ContractError("NONFINITE_CELL_PREDICTION")
    return result


def interpolate_columns(cell_frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    required = set(STATION_KEYS + ["weight", *columns])
    if not required.issubset(cell_frame):
        raise ContractError(f"INTERPOLATION_SCHEMA_MISSING:{sorted(required - set(cell_frame.columns))}")
    weighted = cell_frame[STATION_KEYS].copy()
    for column in columns:
        weighted[column] = cell_frame[column].to_numpy(float) * cell_frame.weight.to_numpy(float)
    return weighted.groupby(STATION_KEYS, as_index=False)[columns].sum()


def reconstruct_wind_cells(along: pd.DataFrame, cross: pd.DataFrame) -> pd.DataFrame:
    merged = along.merge(cross[CELL_KEYS + ["Rcross_predicted_residual"]], on=CELL_KEYS, validate="one_to_one")
    required = {"U10_background", "V10_background", "cos_wdir_background", "sin_wdir_background"}
    if not required.issubset(merged):
        raise ContractError(f"WIND_CELL_SCHEMA_MISSING:{sorted(required - set(merged.columns))}")
    u, v, speed = reconstruct_wind(
        merged.U10_background,
        merged.V10_background,
        merged.Ralong_predicted_residual,
        merged.Rcross_predicted_residual,
        merged.cos_wdir_background,
        merged.sin_wdir_background,
    )
    merged["U10_corrected"] = u
    merged["V10_corrected"] = v
    merged["WindSpeed_corrected"] = speed
    merged["WindSpeed_background"] = np.hypot(merged.U10_background, merged.V10_background)
    return merged

