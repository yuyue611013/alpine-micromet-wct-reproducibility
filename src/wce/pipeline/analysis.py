"""Aggregate scientific endpoints for authorized prepared-input OOF outputs."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from wce.contracts.scientific import (
    ContractError,
    metrics,
    paired_station_cluster_bootstrap,
    wct_celsius,
    wct_piecewise_sensitivity,
)


def paired_metrics(frame: pd.DataFrame, observed: str, background: str, corrected: str) -> dict[str, Any]:
    baseline = metrics(frame[observed], frame[background])
    adjusted = metrics(frame[observed], frame[corrected])
    return {
        "n": baseline["n"],
        "background": baseline,
        "corrected": adjusted,
        "delta_rmse_bg_minus_corrected": baseline["rmse"] - adjusted["rmse"],
        "delta_mae_bg_minus_corrected": baseline["mae"] - adjusted["mae"],
        "bias_shift_corrected_minus_bg": adjusted["bias"] - baseline["bias"],
    }


def component_metrics_table(temperature: pd.DataFrame, dewpoint: pd.DataFrame, wind: pd.DataFrame) -> pd.DataFrame:
    specifications = component_specifications(temperature, dewpoint, wind)
    rows = []
    for variable, frame, observed, background, corrected in specifications:
        result = paired_metrics(frame, observed, background, corrected)
        rows.append(_flatten_metric_result(variable, result))
    return pd.DataFrame(rows)


def component_specifications(
    temperature: pd.DataFrame, dewpoint: pd.DataFrame, wind: pd.DataFrame
) -> list[tuple[str, pd.DataFrame, str, str, str]]:
    return [
        ("Temperature", temperature, "T_observed", "T_background", "T_corrected"),
        ("Dew_point_constrained", dewpoint, "Td_observed", "Td_background", "Td_corrected_constrained"),
        ("U10", wind, "U10_observed", "U10_background", "U10_corrected"),
        ("V10", wind, "V10_observed", "V10_background", "V10_corrected"),
        ("Wind_speed", wind, "WindSpeed_observed", "WindSpeed_background", "WindSpeed_corrected"),
    ]


def _flatten_metric_result(variable: str, result: dict[str, Any], **groups: Any) -> dict[str, Any]:
    return {
        "variable": variable,
        **groups,
        "n": result["n"],
        **{f"background_{key}": value for key, value in result["background"].items() if key != "n"},
        **{f"corrected_{key}": value for key, value in result["corrected"].items() if key != "n"},
        "delta_rmse_bg_minus_corrected": result["delta_rmse_bg_minus_corrected"],
        "delta_mae_bg_minus_corrected": result["delta_mae_bg_minus_corrected"],
        "bias_shift_corrected_minus_bg": result["bias_shift_corrected_minus_bg"],
    }


def component_metrics_monthly(temperature: pd.DataFrame, dewpoint: pd.DataFrame, wind: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variable, frame, observed, background, corrected in component_specifications(temperature, dewpoint, wind):
        timestamp = pd.to_datetime(frame["time_utc"], utc=True, errors="raise")
        for month in sorted(timestamp.dt.month.unique()):
            subset = frame.loc[timestamp.dt.month.eq(month)]
            rows.append(_flatten_metric_result(variable, paired_metrics(subset, observed, background, corrected), month=int(month)))
    return pd.DataFrame(rows)


def component_metrics_by_station(temperature: pd.DataFrame, dewpoint: pd.DataFrame, wind: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variable, frame, observed, background, corrected in component_specifications(temperature, dewpoint, wind):
        for station_id, subset in frame.groupby("station_id", sort=True):
            rows.append(_flatten_metric_result(variable, paired_metrics(subset, observed, background, corrected), station_id=str(station_id)))
    return pd.DataFrame(rows)


def component_metrics_by_groups(
    temperature: pd.DataFrame,
    dewpoint: pd.DataFrame,
    wind: pd.DataFrame,
    group_columns: tuple[str, ...] = ("mismatch_group", "elevation_group"),
) -> pd.DataFrame:
    rows = []
    for variable, frame, observed, background, corrected in component_specifications(temperature, dewpoint, wind):
        for group_column in group_columns:
            if group_column not in frame:
                raise ContractError(f"REPRESENTATIVENESS_GROUP_COLUMN_MISSING:{group_column}")
            for group_value, subset in frame.groupby(group_column, sort=True):
                rows.append(
                    _flatten_metric_result(
                        variable,
                        paired_metrics(subset, observed, background, corrected),
                        group_type=group_column,
                        group=str(group_value),
                    )
                )
    return pd.DataFrame(rows)


def component_bootstrap(
    temperature: pd.DataFrame,
    dewpoint: pd.DataFrame,
    wind: pd.DataFrame,
    replicates: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    replicate_tables, summaries = [], []
    for variable, frame, observed, background, corrected in component_specifications(temperature, dewpoint, wind):
        draws = paired_station_cluster_bootstrap(frame, observed, background, corrected, replicates=replicates, seed=seed)
        draws.insert(0, "variable", variable)
        replicate_tables.append(draws)
        point = paired_metrics(frame, observed, background, corrected)
        for endpoint, estimate_key, draw_column in (
            ("delta_rmse", "delta_rmse_bg_minus_corrected", "delta_rmse"),
            ("delta_mae", "delta_mae_bg_minus_corrected", "delta_mae"),
            ("bias_shift", "bias_shift_corrected_minus_bg", "bias_shift"),
        ):
            summaries.append(
                {
                    "variable": variable,
                    "endpoint": endpoint,
                    "estimate": point[estimate_key],
                    "ci_low": float(draws[draw_column].quantile(0.025)),
                    "ci_high": float(draws[draw_column].quantile(0.975)),
                    "replicates": int(replicates),
                    "seed": int(seed),
                    "paired_station_draws": True,
                }
            )
    return pd.concat(replicate_tables, ignore_index=True), pd.DataFrame(summaries)


def primary_wct_table(temperature: pd.DataFrame, wind: pd.DataFrame) -> pd.DataFrame:
    keys = ["station_id", "time_utc", "fold"]
    merged = temperature[keys + ["T_observed", "T_background", "T_corrected"]].merge(
        wind[keys + ["WindSpeed_observed", "WindSpeed_background", "WindSpeed_corrected"]],
        on=keys,
        validate="one_to_one",
    )
    if merged.duplicated(keys).any():
        raise ContractError("WCT_DUPLICATE_KEY")
    merged = merged[merged.T_observed <= 0].copy()
    merged["WCT_observed"] = wct_celsius(merged.T_observed, merged.WindSpeed_observed)
    merged["WCT_background"] = wct_celsius(merged.T_background, merged.WindSpeed_background)
    merged["WCT_corrected"] = wct_celsius(merged.T_corrected, merged.WindSpeed_corrected)
    return merged


def wct_summaries(wct: pd.DataFrame, replicates: int, seed: int) -> tuple[dict[str, Any], dict[str, Any]]:
    primary = paired_metrics(wct, "WCT_observed", "WCT_background", "WCT_corrected")
    bootstrap = paired_station_cluster_bootstrap(
        wct, "WCT_observed", "WCT_background", "WCT_corrected", replicates=replicates, seed=seed
    )
    bootstrap_summary = {
        "replicates": replicates,
        "seed": seed,
        "paired_station_draws": True,
    }
    for endpoint, estimate_key, draw_column in (
        ("delta_rmse", "delta_rmse_bg_minus_corrected", "delta_rmse"),
        ("delta_mae", "delta_mae_bg_minus_corrected", "delta_mae"),
        ("bias_shift", "bias_shift_corrected_minus_bg", "bias_shift"),
    ):
        bootstrap_summary[endpoint] = {
            "estimate": primary[estimate_key],
            "ci_low": float(bootstrap[draw_column].quantile(0.025)),
            "ci_high": float(bootstrap[draw_column].quantile(0.975)),
        }
    piecewise = wct[["station_id", "time_utc", "fold"]].copy()
    piecewise["WCT_observed"] = wct_piecewise_sensitivity(wct.T_observed, wct.WindSpeed_observed)
    piecewise["WCT_background"] = wct_piecewise_sensitivity(wct.T_background, wct.WindSpeed_background)
    piecewise["WCT_corrected"] = wct_piecewise_sensitivity(wct.T_corrected, wct.WindSpeed_corrected)
    return (
        {
            "endpoint": "PRIMARY_STANDARD_CELSIUS_WCT",
            "cohort": "observed_temperature_le_0C",
            "wind_conversion": "m_s-1_to_km_h-1",
            "numerical_floor_ms": 0.1,
            "wind_height_adjustment": False,
            "metrics": primary,
        },
        {"bootstrap": bootstrap_summary, "piecewise_sensitivity": paired_metrics(piecewise, "WCT_observed", "WCT_background", "WCT_corrected")},
    )


def direct_wct_comparison(
    component_wct: pd.DataFrame,
    frozen_direct: pd.DataFrame,
    scenario: str = "all_stations",
    excluded_stations: set[str] | None = None,
) -> pd.DataFrame:
    keys = ["station_id", "time_utc", "fold"]
    direct_required = set(keys + ["WCT_observed", "WCT_background", "WCT_corrected"])
    if not direct_required.issubset(frozen_direct):
        raise ContractError("FROZEN_DIRECT_WCT_SCHEMA_MISMATCH")
    component_input, direct_input = component_wct.copy(), frozen_direct.copy()
    if excluded_stations:
        excluded = {str(value) for value in excluded_stations}
        component_input = component_input.loc[~component_input.station_id.astype(str).isin(excluded)]
        direct_input = direct_input.loc[~direct_input.station_id.astype(str).isin(excluded)]
    merged = component_input.merge(direct_input[sorted(direct_required)], on=keys, suffixes=("_component", "_direct"), validate="one_to_one")
    if merged.empty:
        raise ContractError("NO_MATCHED_DIRECT_WCT_KEYS")
    component = paired_metrics(merged, "WCT_observed_component", "WCT_background_component", "WCT_corrected_component")
    direct = paired_metrics(merged, "WCT_observed_direct", "WCT_background_direct", "WCT_corrected_direct")
    return pd.DataFrame([
        _flatten_metric_result("component_WCT", component, scenario=scenario, pathway="component", background_representation="component_station_stencil"),
        _flatten_metric_result("direct_WCT_own_background", direct, scenario=scenario, pathway="direct", background_representation="frozen_direct_station_table"),
    ])
