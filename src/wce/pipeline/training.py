"""Nested LightGBM fitting with outer-fold isolation and fixed-round refits."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from wce.contracts.io import sha256_file
from wce.contracts.scientific import ContractError, nested_fold_plan, selected_rounds


def fit_nested_target(
    frame: pd.DataFrame,
    fold_map: pd.DataFrame,
    mismatch_stations: set[str],
    target_name: str,
    target_column: str,
    feature_columns: list[str],
    exclude_mismatch: bool,
    parameters: dict[str, Any],
    maximum_rounds: int,
    early_stopping_rounds: int,
    seed: int,
    threads: int,
    output_root: str | Path,
) -> dict[int, Path]:
    try:
        import lightgbm as lgb
    except ImportError as exc:
        raise ContractError("LIGHTGBM_REQUIRED_FOR_FULL_PIPELINE") from exc
    required = {"station_id", target_column, *feature_columns}
    if not required.issubset(frame.columns):
        raise ContractError(f"TRAINING_SCHEMA_MISSING:{target_name}:{sorted(required - set(frame.columns))}")
    if not np.isfinite(frame[feature_columns].to_numpy(float)).all():
        raise ContractError(f"NONFINITE_TRAINING_FEATURES:{target_name}")
    plans = nested_fold_plan(fold_map, mismatch_stations, exclude_mismatch)
    params = dict(parameters)
    params.update({"seed": int(seed), "num_threads": int(threads)})
    root = Path(output_root) / "models" / target_name
    root.mkdir(parents=True, exist_ok=False)
    models: dict[int, Path] = {}
    for plan in plans:
        outer = int(plan["outer_fold"])
        best_iterations = []
        inner_records = []
        for inner in plan["inner_runs"]:
            train_mask = frame.station_id.astype(str).isin(inner["training_stations"])
            validation_mask = frame.station_id.astype(str).isin(inner["validation_stations"])
            if not train_mask.any() or not validation_mask.any():
                raise ContractError(f"EMPTY_INNER_DATASET:{target_name}:{outer}")
            train_set = lgb.Dataset(frame.loc[train_mask, feature_columns], label=frame.loc[train_mask, target_column])
            validation_set = lgb.Dataset(frame.loc[validation_mask, feature_columns], label=frame.loc[validation_mask, target_column], reference=train_set)
            booster = lgb.train(
                params,
                train_set,
                num_boost_round=int(maximum_rounds),
                valid_sets=[validation_set],
                valid_names=["inner_validation"],
                callbacks=[lgb.early_stopping(int(early_stopping_rounds), verbose=False), lgb.log_evaluation(period=0)],
            )
            best = int(booster.best_iteration or booster.current_iteration())
            best_iterations.append(best)
            inner_records.append({"validation_fold": inner["validation_fold"], "best_iteration": best, "outer_fold_access": False})
        rounds = selected_rounds(best_iterations)
        final_mask = frame.station_id.astype(str).isin(plan["final_training_stations"])
        final_set = lgb.Dataset(frame.loc[final_mask, feature_columns], label=frame.loc[final_mask, target_column])
        final_model = lgb.train(params, final_set, num_boost_round=rounds, valid_sets=None, callbacks=[lgb.log_evaluation(period=0)])
        fold_dir = root / f"outer_fold_{outer}"
        fold_dir.mkdir(parents=True, exist_ok=False)
        model_path = fold_dir / "booster.lgb"
        final_model.save_model(str(model_path), num_iteration=rounds)
        (fold_dir / "feature_list.json").write_text(json.dumps(feature_columns, indent=2) + "\n", encoding="utf-8")
        manifest = {
            "status": "SUCCESS",
            "target": target_name,
            "outer_fold": outer,
            "inner_results": inner_records,
            "selected_rounds": rounds,
            "final_refit_validation_dataset": None,
            "final_refit_early_stopping": False,
            "training_seed": seed,
            "training_station_count": len(plan["final_training_stations"]),
            "prediction_station_count": len(plan["prediction_stations"]),
            "zero_station_overlap": not bool(set(plan["final_training_stations"]) & set(plan["prediction_stations"])),
            "model_relative_path": model_path.relative_to(Path(output_root)).as_posix(),
            "model_sha256": sha256_file(model_path),
        }
        (fold_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        models[outer] = model_path
    return models

