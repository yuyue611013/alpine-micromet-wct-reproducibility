"""Pure numerical and routing contracts locked to WCE_SCIENTIFIC_CORRECTION_V1."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd


TRAINING_SEED = 20260127
BOOTSTRAP_SEED = 20260825
BOOTSTRAP_REPLICATES = 2000


class ContractError(RuntimeError):
    """Raised when a locked scientific or safety contract is violated."""


def _normalized_ssrd_unit(unit: str) -> str:
    return "".join(str(unit).lower().split()).replace("joules", "j")


def convert_ssrd_to_wm2(values: Any, raw_units: str) -> np.ndarray:
    """Convert hourly accumulated SSRD to W m-2 and stop on unknown units."""
    normalized = _normalized_ssrd_unit(raw_units)
    accepted = {"jm**-2", "jm-2", "j/m2", "jm^-2"}
    if normalized not in accepted:
        raise ContractError(f"UNKNOWN_SSRD_UNITS:{raw_units!r}")
    result = np.asarray(values, dtype=np.float64) / 3600.0
    if not np.isfinite(result).all():
        raise ContractError("NONFINITE_SSRD_AFTER_CONVERSION")
    return result


def selected_rounds(best_iterations: Iterable[int]) -> int:
    ordered = sorted(int(value) for value in best_iterations)
    if len(ordered) != 4 or ordered[0] < 1:
        raise ContractError("FOUR_POSITIVE_INNER_BEST_ITERATIONS_REQUIRED")
    return int(math.floor((ordered[1] + ordered[2]) / 2.0 + 0.5))


def validate_station_fold_map(
    frame: pd.DataFrame,
    expected_station_count: int = 74,
    expected_counts: tuple[int, ...] = (15, 15, 15, 15, 14),
) -> pd.DataFrame:
    required = {"station_id", "fold"}
    if not required.issubset(frame.columns):
        raise ContractError(f"FOLD_MAP_MISSING_COLUMNS:{sorted(required - set(frame.columns))}")
    result = frame[["station_id", "fold"]].copy()
    result["station_id"] = result["station_id"].astype(str).str.strip()
    result["fold"] = pd.to_numeric(result["fold"], errors="raise").astype(int)
    if result["station_id"].eq("").any() or result["station_id"].duplicated().any():
        raise ContractError("STATION_ASSIGNED_TO_MULTIPLE_FOLDS")
    if set(result["fold"]) != set(range(5)):
        raise ContractError("FIVE_FOLDS_REQUIRED")
    counts = tuple(int((result["fold"] == fold).sum()) for fold in range(5))
    if len(result) != expected_station_count or counts != expected_counts:
        raise ContractError(f"STATION_FOLD_COUNT_CHANGED:{len(result)}:{counts}")
    return result.sort_values("station_id").reset_index(drop=True)


def nested_fold_plan(
    fold_map: pd.DataFrame,
    mismatch_stations: set[str],
    exclude_mismatch_from_training: bool,
) -> list[dict[str, Any]]:
    checked = validate_station_fold_map(fold_map)
    all_stations = set(checked["station_id"])
    mismatch = {str(value).strip() for value in mismatch_stations}
    if not mismatch.issubset(all_stations):
        raise ContractError("MISMATCH_STATION_NOT_IN_FOLD_MAP")
    plans: list[dict[str, Any]] = []
    predicted: list[str] = []
    for outer_fold in range(5):
        prediction = set(checked.loc[checked["fold"] == outer_fold, "station_id"])
        eligible = all_stations - prediction
        if exclude_mismatch_from_training:
            eligible -= mismatch
        inner_runs = []
        for inner_fold in range(5):
            if inner_fold == outer_fold:
                continue
            validation = set(checked.loc[checked["fold"] == inner_fold, "station_id"]) & eligible
            training = eligible - validation
            if prediction & (training | validation) or training & validation:
                raise ContractError("OUTER_OR_INNER_STATION_LEAKAGE")
            inner_runs.append(
                {
                    "validation_fold": inner_fold,
                    "training_stations": sorted(training),
                    "validation_stations": sorted(validation),
                }
            )
        if len(inner_runs) != 4:
            raise ContractError("FOUR_INNER_VALIDATIONS_REQUIRED")
        plans.append(
            {
                "outer_fold": outer_fold,
                "prediction_stations": sorted(prediction),
                "final_training_stations": sorted(eligible),
                "inner_runs": inner_runs,
                "outer_fold_zero_access": True,
            }
        )
        predicted.extend(prediction)
    if len(predicted) != len(all_stations) or len(set(predicted)) != len(all_stations):
        raise ContractError("EACH_STATION_MUST_BE_PREDICTED_ONCE")
    return plans


def constrain_dewpoint_same_fold(temperature: pd.DataFrame, dewpoint: pd.DataFrame) -> pd.DataFrame:
    keys = ["station_id", "time_utc", "fold"]
    t_required = set(keys + ["T_corrected"])
    d_required = set(keys + ["Td_corrected_unconstrained"])
    if not t_required.issubset(temperature) or not d_required.issubset(dewpoint):
        raise ContractError("TD_CONSTRAINT_SCHEMA_MISMATCH")
    if temperature.duplicated(keys).any() or dewpoint.duplicated(keys).any():
        raise ContractError("TD_CONSTRAINT_DUPLICATE_KEY")
    merged = dewpoint.merge(temperature[keys + ["T_corrected"]], on=keys, validate="one_to_one")
    if len(merged) != len(temperature) or len(merged) != len(dewpoint):
        raise ContractError("TD_T_KEY_OR_FOLD_MISMATCH")
    merged["Td_corrected_constrained"] = np.minimum(
        merged["Td_corrected_unconstrained"].to_numpy(float),
        merged["T_corrected"].to_numpy(float),
    )
    return merged


def rotate_along_cross_to_uv(
    along_residual: Any, cross_residual: Any, cos_wdir_background: Any, sin_wdir_background: Any
) -> tuple[np.ndarray, np.ndarray]:
    along = np.asarray(along_residual, dtype=float)
    cross = np.asarray(cross_residual, dtype=float)
    cosine = np.asarray(cos_wdir_background, dtype=float)
    sine = np.asarray(sin_wdir_background, dtype=float)
    return along * cosine - cross * sine, along * sine + cross * cosine


def reconstruct_wind(
    u_background: Any,
    v_background: Any,
    along_residual: Any,
    cross_residual: Any,
    cos_wdir_background: Any,
    sin_wdir_background: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    u_residual, v_residual = rotate_along_cross_to_uv(
        along_residual, cross_residual, cos_wdir_background, sin_wdir_background
    )
    u = np.asarray(u_background, dtype=float) + u_residual
    v = np.asarray(v_background, dtype=float) + v_residual
    return u, v, np.hypot(u, v)


def wct_celsius(temperature_c: Any, wind_speed_ms: Any) -> np.ndarray:
    temperature = np.asarray(temperature_c, dtype=float)
    wind_kmh = np.maximum(np.asarray(wind_speed_ms, dtype=float), 0.1) * 3.6
    power = wind_kmh**0.16
    return 13.12 + 0.6215 * temperature - 11.37 * power + 0.3965 * temperature * power


def wct_piecewise_sensitivity(temperature_c: Any, wind_speed_ms: Any) -> np.ndarray:
    temperature = np.asarray(temperature_c, dtype=float)
    wind_kmh = np.asarray(wind_speed_ms, dtype=float) * 3.6
    result = np.full(temperature.shape, np.nan)
    valid = np.isfinite(temperature) & np.isfinite(wind_kmh) & (wind_kmh >= 0)
    calm = valid & (wind_kmh == 0)
    low = valid & (wind_kmh > 0) & (wind_kmh < 5)
    standard = valid & (wind_kmh >= 5)
    result[calm] = temperature[calm]
    result[low] = temperature[low] + ((-1.59 + 0.1345 * temperature[low]) / 5) * wind_kmh[low]
    power = wind_kmh[standard] ** 0.16
    result[standard] = (
        13.12
        + 0.6215 * temperature[standard]
        - 11.37 * power
        + 0.3965 * temperature[standard] * power
    )
    return result


def metrics(observed: Any, predicted: Any) -> dict[str, float | int]:
    obs = np.asarray(observed, dtype=float)
    pred = np.asarray(predicted, dtype=float)
    valid = np.isfinite(obs) & np.isfinite(pred)
    obs, pred = obs[valid], pred[valid]
    if not len(obs):
        raise ContractError("NO_FINITE_METRIC_PAIRS")
    residual = pred - obs
    total = float(np.sum((obs - obs.mean()) ** 2))
    return {
        "n": int(len(obs)),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "mae": float(np.mean(np.abs(residual))),
        "bias": float(np.mean(residual)),
        "r2": float(1 - np.sum(residual**2) / total) if total > 0 else float("nan"),
    }


def paired_station_cluster_bootstrap(
    frame: pd.DataFrame,
    observed: str,
    background: str,
    corrected: str,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
    station_column: str = "station_id",
) -> pd.DataFrame:
    groups = {str(key): group for key, group in frame.groupby(station_column, sort=True)}
    stations = sorted(groups)
    if not stations:
        raise ContractError("NO_STATION_CLUSTERS")
    rng = np.random.default_rng(seed)
    rows = []
    for replicate in range(int(replicates)):
        draw = rng.choice(stations, size=len(stations), replace=True)
        sample = pd.concat([groups[station] for station in draw], ignore_index=True)
        background_metrics = metrics(sample[observed], sample[background])
        corrected_metrics = metrics(sample[observed], sample[corrected])
        rows.append(
            {
                "replicate": replicate,
                "delta_rmse": background_metrics["rmse"] - corrected_metrics["rmse"],
                "delta_mae": background_metrics["mae"] - corrected_metrics["mae"],
                "bias_shift": corrected_metrics["bias"] - background_metrics["bias"],
            }
        )
    return pd.DataFrame(rows)

