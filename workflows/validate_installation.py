#!/usr/bin/env python3
"""Dependency and synthetic scientific-contract validation; performs no training or external I/O."""

from __future__ import annotations

import argparse
import importlib.metadata
import json

import numpy as np
import pandas as pd

from wce.contracts.scientific import (
    constrain_dewpoint_same_fold,
    convert_ssrd_to_wm2,
    nested_fold_plan,
    reconstruct_wind,
    selected_rounds,
    validate_station_fold_map,
    wct_celsius,
)
from wce.stencil.backend import interpolate_four, locate_four_cells


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--full", action="store_true", help="Also check authorized-prepared-input pipeline dependencies")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    packages = {}
    for package in ("numpy", "pandas"):
        packages[package] = importlib.metadata.version(package)
    if args.full:
        for package in ("pyarrow", "lightgbm", "xarray", "netCDF4", "pyproj"):
            packages[package] = importlib.metadata.version(package)
    converted = convert_ssrd_to_wm2([0.0, 3600.0, 7200.0], "J m**-2")
    if not np.array_equal(converted, [0.0, 1.0, 2.0]):
        raise AssertionError("SSRD fixture failed")
    stations = [f"S{index:03d}" for index in range(74)]
    folds = [0] * 15 + [1] * 15 + [2] * 15 + [3] * 15 + [4] * 14
    fold_map = validate_station_fold_map(pd.DataFrame({"station_id": stations, "fold": folds}))
    plans = nested_fold_plan(fold_map, set(stations[:17]), True)
    if len(plans) != 5 or any(set(plan["prediction_stations"]) & set(plan["final_training_stations"]) for plan in plans):
        raise AssertionError("Nested fold fixture failed")
    if selected_rounds([10, 20, 21, 100]) != 21:
        raise AssertionError("Selected-round fixture failed")
    location = locate_four_cells(np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0, 2.0]), np.array([0.5]), np.array([0.5]))[0]
    if not location["valid"] or not np.isclose(sum(location["weights"]), 1.0):
        raise AssertionError("Four-cell geometry fixture failed")
    if not np.isclose(interpolate_four([1, 2, 3, 4], [0.25] * 4), 2.5):
        raise AssertionError("Four-cell interpolation fixture failed")
    keys = {"station_id": ["A"], "time_utc": ["2025-01-01T00:00:00"], "fold": [0]}
    constrained = constrain_dewpoint_same_fold(
        pd.DataFrame({**keys, "T_corrected": [-2.0]}),
        pd.DataFrame({**keys, "Td_corrected_unconstrained": [-1.0]}),
    )
    if constrained.Td_corrected_constrained.iloc[0] != -2.0:
        raise AssertionError("Td constraint fixture failed")
    u, v, speed = reconstruct_wind([1.0], [2.0], [1.0], [0.0], [1.0], [0.0])
    if not (np.isclose(u[0], 2.0) and np.isclose(v[0], 2.0) and np.isclose(speed[0], np.sqrt(8))):
        raise AssertionError("Wind reconstruction fixture failed")
    expected = 13.12 + 0.6215 * -10.0 - 11.37 * (36.0**0.16) + 0.3965 * -10.0 * (36.0**0.16)
    if not np.isclose(wct_celsius([-10.0], [10.0])[0], expected):
        raise AssertionError("WCT fixture failed")
    print(json.dumps({"status": "PASS", "dependency_tier": "FULL" if args.full else "PUBLIC_CORE", "dependencies": packages, "training_run": False, "external_data_access": False, "full_grid_run": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
