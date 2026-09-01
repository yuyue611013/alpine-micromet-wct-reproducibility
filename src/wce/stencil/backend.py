"""Four-cell geometry and temporal-state operators used by prepared-input OOF prediction."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

from wce.contracts.scientific import ContractError, convert_ssrd_to_wm2


def locate_four_cells(
    x_native: np.ndarray, y_native: np.ndarray, x_points: np.ndarray, y_points: np.ndarray
) -> list[dict[str, Any]]:
    """Apply the locked search/clip rules and return native-grid indices and weights."""
    x_native = np.asarray(x_native)
    y_native = np.asarray(y_native)
    x_reverse = bool(x_native[0] > x_native[-1])
    y_reverse = bool(y_native[0] > y_native[-1])
    x = x_native[::-1] if x_reverse else x_native
    y = y_native[::-1] if y_reverse else y_native
    output = []
    for x_point, y_point in zip(np.asarray(x_points, float), np.asarray(y_points, float)):
        ix1 = int(np.searchsorted(x, x_point, side="right"))
        iy1 = int(np.searchsorted(y, y_point, side="right"))
        if not (0 < ix1 < len(x) and 0 < iy1 < len(y)):
            output.append({"valid": False, "cells": [], "weights": []})
            continue
        ix0, iy0 = ix1 - 1, iy1 - 1
        wx = float(np.clip((x_point - x[ix0]) / (x[ix1] - x[ix0] + 1e-12), 0.0, 1.0))
        wy = float(np.clip((y_point - y[iy0]) / (y[iy1] - y[iy0] + 1e-12), 0.0, 1.0))
        ascending_cells = [(iy0, ix0), (iy0, ix1), (iy1, ix0), (iy1, ix1)]
        weights = [(1 - wx) * (1 - wy), wx * (1 - wy), (1 - wx) * wy, wx * wy]
        cells = [
            (len(y) - 1 - row if y_reverse else row, len(x) - 1 - col if x_reverse else col)
            for row, col in ascending_cells
        ]
        output.append({"valid": True, "cells": cells, "weights": weights})
    return output


def deduplicate_cells(locations: Iterable[dict[str, Any]]) -> list[tuple[int, int]]:
    return sorted({tuple(cell) for item in locations if item["valid"] for cell in item["cells"]})


def interpolate_four(values: Iterable[float], weights: Iterable[float]) -> np.float32:
    values_array = np.asarray(list(values))
    weights_array = np.asarray(list(weights), dtype=float)
    if len(values_array) != 4 or len(weights_array) != 4:
        raise ContractError("FOUR_VALUES_AND_WEIGHTS_REQUIRED")
    if not np.isfinite(values_array).all():
        raise ContractError("NONFINITE_CELL_VALUE")
    if not np.isclose(weights_array.sum(), 1.0, rtol=0.0, atol=1e-12):
        raise ContractError("FOUR_CELL_WEIGHTS_MUST_SUM_TO_ONE")
    return np.float32(np.sum(values_array * weights_array))


def build_monthly_feature_state(
    time_hour: np.ndarray,
    base_features: dict[str, np.ndarray],
    feature_order: list[str],
    raw_ssrd_units: str,
) -> np.ndarray:
    """Small portable operator illustrating conversion-before-lag/rolling semantics.

    Prepared full-pipeline inputs may supply additional locked features, but every SSRD-derived
    current/lag/change/rolling value must originate from the converted W m-2 array here.
    State is reset on every function call, which represents one calendar month.
    """
    if "SSRD_raw" not in base_features:
        raise ContractError("SSRD_RAW_REQUIRED_FOR_FEATURE_STATE")
    converted = convert_ssrd_to_wm2(base_features["SSRD_raw"], raw_ssrd_units)
    values = dict(base_features)
    values["SSRD_bg_Wm2"] = converted
    values["SSRD_bg_Wm2_lag1h"] = np.concatenate([converted[:1], converted[:-1]])
    values["d1h_SSRD_bg_Wm2"] = converted - values["SSRD_bg_Wm2_lag1h"]
    values["sin_hour"] = np.sin(2 * np.pi * np.asarray(time_hour, float) / 24.0)
    values["cos_hour"] = np.cos(2 * np.pi * np.asarray(time_hour, float) / 24.0)
    missing = [name for name in feature_order if name not in values]
    if missing:
        raise ContractError(f"PREPARED_FEATURES_MISSING:{missing}")
    matrix = np.column_stack([np.asarray(values[name], dtype=np.float32) for name in feature_order])
    if not np.isfinite(matrix).all():
        raise ContractError("NONFINITE_PREPARED_FEATURE_MATRIX")
    return np.ascontiguousarray(matrix, dtype=np.float32)

