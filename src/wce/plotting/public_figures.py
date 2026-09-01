"""Aggregate-only renderers for current public manuscript figures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from wce.contracts.io import write_json_once
from wce.contracts.scientific import ContractError


BASELINE = "#7F7F7F"
COMPONENT = "#2878B5"
DIRECT = "#D97A1E"
EDGE = "#222222"
POSITIVE = "#4C956C"
NEGATIVE = "#C44E52"
VARIABLE_COLORS = {"Temperature": "#D1495B", "Dew point": "#2878B5", "Wind speed": "#4C956C"}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.3,
            "axes.labelsize": 9.5,
            "axes.titlesize": 10.0,
            "xtick.labelsize": 8.4,
            "ytick.labelsize": 8.4,
            "legend.fontsize": 8.4,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _axis(ax, grid: str = "y") -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis=grid, color="#D9D9D9", linewidth=0.5, alpha=0.55)
    ax.set_axisbelow(True)


def _panel(ax, label: str) -> None:
    ax.text(-0.13, 1.05, label, transform=ax.transAxes, fontsize=11, fontweight="bold", va="top")


def _labels(ax, bars) -> None:
    for bar in bars:
        value = float(bar.get_height())
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.3f}", ha="center", va="bottom", fontsize=7.5)


def _save(fig, output_dir: Path, stem: str, sources: list[Path], contract: dict) -> list[Path]:
    png = output_dir / f"{stem}.png"
    pdf = output_dir / f"{stem}.pdf"
    manifest = output_dir / f"{stem}_manifest.json"
    for target in (png, pdf, manifest):
        if target.exists():
            raise ContractError(f"NON_CLOBBER:{target}")
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    write_json_once(
        manifest,
        {
            "status": "PASS",
            "aggregate_only": True,
            "contains_row_level_data": False,
            "sources": [{"relative_name": path.name, "sha256": _sha(path)} for path in sources],
            "outputs": [{"name": png.name, "sha256": _sha(png)}, {"name": pdf.name, "sha256": _sha(pdf)}],
            "contract": contract,
        },
    )
    return [png, pdf, manifest]


def _paired_bars(ax, labels, background, corrected, ylabel, width=0.32):
    x = np.arange(len(labels))
    bg = ax.bar(x - width / 2, background, width, color=BASELINE, edgecolor=EDGE, linewidth=0.45)
    corr = ax.bar(x + width / 2, corrected, width, color=COMPONENT, edgecolor=EDGE, linewidth=0.45)
    ax.set_xticks(x, labels)
    ax.set_ylabel(ylabel)
    low = min(0.0, min(background), min(corrected))
    high = max(list(background) + list(corrected))
    ax.set_ylim(low - (0.12 * high if low < 0 else 0), high * 1.22)
    _axis(ax)
    _labels(ax, bg)
    _labels(ax, corr)
    return bg, corr


def _figure_1(source_dir: Path, output_dir: Path) -> list[Path]:
    source = source_dir / "main_figure_1_environmental_metrics_v2.csv"
    data = pd.read_csv(source)
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.9))
    bars = _paired_bars(
        axes[0],
        ["Temperature", "Dew point"],
        data.set_index("variable").loc[["Temperature", "Dew point"], "background_rmse"].tolist(),
        data.set_index("variable").loc[["Temperature", "Dew point"], "corrected_rmse"].tolist(),
        "RMSE (°C)",
    )
    wind = data.set_index("variable").loc[["U10", "V10", "Wind speed"]]
    _paired_bars(axes[1], ["U10", "V10", "Wind speed"], wind.background_rmse.tolist(), wind.corrected_rmse.tolist(), "RMSE (m s$^{-1}$)")
    _panel(axes[0], "a")
    _panel(axes[1], "b")
    fig.legend([bars[0][0], bars[1][0]], ["ERA5-Land", "Component-corrected"], loc="upper center", ncol=2, frameon=False)
    fig.subplots_adjust(top=0.82, bottom=0.16, wspace=0.28)
    return _save(fig, output_dir, "Figure_2_component_RMSE", [source], {"mapping": "manuscript Figure 2", "panels": ["a", "b"]})


def _percent(frame: pd.DataFrame) -> pd.Series:
    return 100.0 * frame.delta_rmse_bg_minus_corrected / frame.background_rmse


def _figure_2(source_dir: Path, output_dir: Path) -> list[Path]:
    month_path = source_dir / "main_figure_2_monthly_metrics_v2.csv"
    group_path = source_dir / "main_figure_2_representativeness_groups_v2.csv"
    month, group = pd.read_csv(month_path), pd.read_csv(group_path)
    variables = ["Temperature", "Dew point", "Wind speed"]
    groups = ["mismatch_regular", "mismatch_mismatch", "aligned_le_100m", "moderate_100_300m", "high_gt_300m"]
    labels = ["Regular", "Mismatch", "Aligned", "Moderate", "High difference"]
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.25))
    for variable in variables:
        data = month[month.variable == variable].copy()
        data["month"] = data.group.str.extract(r"(\d+)").astype(int)
        data = data.sort_values("month")
        axes[0].plot(np.arange(4), _percent(data), marker="o", linewidth=1.8, markersize=5, color=VARIABLE_COLORS[variable], label=variable)
    axes[0].axhline(0, color=EDGE, linewidth=0.8)
    axes[0].set_xticks(range(4), ["Jan", "Feb", "Mar", "Apr"])
    axes[0].set_ylabel("RMSE improvement (%)")
    _axis(axes[0], "both")
    x, width = np.arange(len(groups)), 0.22
    for offset, variable in zip((-width, 0, width), variables):
        data = group[group.variable == variable].set_index("group").loc[groups]
        axes[1].bar(x + offset, _percent(data), width, color=VARIABLE_COLORS[variable], edgecolor=EDGE, linewidth=0.4)
    axes[1].axhline(0, color=EDGE, linewidth=0.8)
    axes[1].axvline(1.5, color=EDGE, linestyle="--", linewidth=0.7, alpha=0.6)
    axes[1].set_xticks(x, labels, rotation=18, ha="right")
    axes[1].set_ylabel("RMSE improvement (%)")
    _axis(axes[1])
    _panel(axes[0], "a")
    _panel(axes[1], "b")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=3, frameon=False)
    fig.subplots_adjust(top=0.82, bottom=0.22, left=0.09, right=0.98, wspace=0.28)
    return _save(fig, output_dir, "Figure_3_monthly_representativeness", [month_path, group_path], {"mapping": "manuscript Figure 3", "panels": ["a", "b"]})


def _figure_3(source_dir: Path, output_dir: Path) -> list[Path]:
    summary_path = source_dir / "main_figure_3_wct_primary_summary_v2.csv"
    strata_path = source_dir / "main_figure_3_wct_strata_v2.csv"
    summary = pd.read_csv(summary_path).iloc[0]
    data = pd.read_csv(strata_path)
    groups = ["mismatch_regular", "mismatch_mismatch", "aligned_le_100m", "moderate_100_300m", "high_gt_300m"]
    labels = ["Regular", "Mismatch", "Aligned", "Moderate", "High difference"]
    fig, axes = plt.subplots(2, 2, figsize=(9.4, 6.8))
    bars = _paired_bars(axes[0, 0], ["RMSE", "MAE"], [summary.background_rmse, summary.background_mae], [summary.corrected_rmse, summary.corrected_mae], "WCT error (°C)")
    offset, width = 0.23, 0.26
    bg = axes[0, 1].bar([-offset], [summary.background_bias], width, color=BASELINE, edgecolor=EDGE, linewidth=0.45)
    corr = axes[0, 1].bar([offset], [summary.corrected_bias], width, color=COMPONENT, edgecolor=EDGE, linewidth=0.45)
    axes[0, 1].set_xticks([0], ["Bias"])
    axes[0, 1].set_xlim(-0.72, 0.72)
    axes[0, 1].set_ylabel("Mean WCT bias (°C)")
    axes[0, 1].axhline(0, color=EDGE, linewidth=0.8)
    axes[0, 1].set_ylim(min(0, summary.background_bias, summary.corrected_bias) - 0.5, max(summary.background_bias, summary.corrected_bias) * 1.22)
    _axis(axes[0, 1]); _labels(axes[0, 1], bg); _labels(axes[0, 1], corr)
    monthly = data[data.stratum_type == "month"].copy()
    monthly["month"] = monthly.stratum.str.extract(r"(\d+)").astype(int)
    monthly = monthly.sort_values("month")
    improvement = 100 * (monthly.background_rmse - monthly.corrected_rmse) / monthly.background_rmse
    axes[1, 0].plot(np.arange(4), improvement, marker="o", color=COMPONENT, linewidth=1.8)
    axes[1, 0].axhline(0, color=EDGE, linewidth=0.8)
    axes[1, 0].set_xticks(range(4), ["Jan", "Feb", "Mar", "Apr"])
    axes[1, 0].set_ylabel("WCT RMSE improvement (%)")
    _axis(axes[1, 0], "both")
    grouped = data[data.stratum.isin(groups)].set_index("stratum").loc[groups]
    values = 100 * (grouped.background_rmse - grouped.corrected_rmse) / grouped.background_rmse
    axes[1, 1].bar(np.arange(5), values, 0.58, color=[POSITIVE if value >= 0 else NEGATIVE for value in values], edgecolor=EDGE, linewidth=0.45)
    axes[1, 1].axhline(0, color=EDGE, linewidth=0.8)
    axes[1, 1].axvline(1.5, color=EDGE, linestyle="--", linewidth=0.7, alpha=0.6)
    axes[1, 1].set_xticks(np.arange(5), labels, rotation=18, ha="right")
    axes[1, 1].set_ylabel("WCT RMSE improvement (%)")
    _axis(axes[1, 1])
    for ax, label in zip(axes.ravel(), "abcd"):
        _panel(ax, label)
    fig.legend([bars[0][0], bars[1][0]], ["ERA5-Land", "Component-corrected"], loc="upper center", ncol=2, frameon=False)
    fig.subplots_adjust(top=0.89, bottom=0.13, left=0.10, right=0.98, wspace=0.30, hspace=0.38)
    return _save(fig, output_dir, "Figure_4_primary_WCT", [summary_path, strata_path], {"mapping": "manuscript Figure 4", "panels": list("abcd"), "primary_endpoint": True})


def _figure_4(source_dir: Path, output_dir: Path) -> list[Path]:
    direct_path = source_dir / "main_figure_4_direct_wct_v2.csv"
    external_path = source_dir / "main_figure_4_external_aggregate_v2.csv"
    direct, external = pd.read_csv(direct_path), pd.read_csv(external_path)
    fig, axes = plt.subplots(2, 2, figsize=(9.5, 6.8))
    for ax, group, title in zip(axes[0], ["all_stations", "excluding_mismatch"], ["All stations", "Elevation mismatch excluded"]):
        frame = direct[direct.group == group].set_index("variable")
        values = [frame.loc["component_WCT", "background_rmse"], frame.loc["component_WCT", "corrected_rmse"], frame.loc["direct_WCT_own_background", "background_rmse"], frame.loc["direct_WCT_own_background", "corrected_rmse"]]
        bars = ax.bar(range(4), values, 0.66, color=[BASELINE, COMPONENT, "#969696", DIRECT], edgecolor=EDGE, linewidth=0.45)
        ax.set_xticks(range(4), ["Component\nbackground", "Component\ncorrected", "Direct\nbackground", "Direct\ncorrected"])
        ax.set_ylim(0, max(values) * 1.22); ax.set_title(title); _axis(ax); _labels(ax, bars)
    axes[0, 0].set_ylabel("WCT RMSE (°C)")
    for ax, variables, title in zip(axes[1], [["Temperature", "Dew point", "Wind speed"], ["U10", "V10"]], ["External aggregate: thermal and wind speed", "External aggregate: wind components"]):
        frame = external.set_index("variable").loc[variables]; x = np.arange(len(frame)); width = 0.32
        bg = ax.bar(x - width / 2, frame.background_rmse, width, color=BASELINE, edgecolor=EDGE, linewidth=0.45)
        corr = ax.bar(x + width / 2, frame.corrected_rmse, width, color=COMPONENT, edgecolor=EDGE, linewidth=0.45)
        ax.set_xticks(x, variables); ax.set_ylim(0, max(frame.background_rmse.max(), frame.corrected_rmse.max()) * 1.22); ax.set_title(title); _axis(ax); _labels(ax, bg); _labels(ax, corr)
    axes[1, 0].set_ylabel("External RMSE (native units)")
    for ax, label in zip(axes.ravel(), "abcd"):
        _panel(ax, label)
    fig.text(0.5, 0.018, "Calendar-aligned cross-year operational stress test; not same-year validation.", ha="center", fontsize=8.4)
    fig.subplots_adjust(top=0.88, bottom=0.14, left=0.10, right=0.98, wspace=0.28, hspace=0.42)
    return _save(fig, output_dir, "Figure_5_direct_external", [direct_path, external_path], {"mapping": "manuscript Figure 5", "aggregate_external_only": True, "pathway_backgrounds_differ": True})


def _box(ax, xy, width, height, text, color):
    patch = FancyBboxPatch(xy, width, height, boxstyle="round,pad=0.015,rounding_size=0.02", fc=color, ec=EDGE, lw=1.0)
    ax.add_patch(patch); ax.text(xy[0] + width / 2, xy[1] + height / 2, text, ha="center", va="center", fontsize=9.5)


def _arrow(ax, start, end):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14, lw=1.2, color=EDGE))


def _extended_2(source_dir: Path, output_dir: Path) -> list[Path]:
    source = source_dir / "extended_data_figure_2_workflow_contract_v2.json"
    json.loads(source.read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(10, 5.9)); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    _box(ax, (0.03, 0.69), 0.21, 0.18, "Prepared background + terrain\nSSRD converted before features", "#D9D9D9")
    _box(ax, (0.30, 0.69), 0.22, 0.18, "Strict outer OOF\nFour station-grouped inner folds\nFixed-round refit", "#E5EEF7")
    _box(ax, (0.58, 0.69), 0.18, 0.18, "Four-cell stencil\nT, constrained Td\nrotated wind", "#DDEEDB")
    _box(ax, (0.82, 0.69), 0.15, 0.18, "Primary WCT\nand uncertainty", "#FCEADB")
    _arrow(ax, (0.24, 0.78), (0.30, 0.78)); _arrow(ax, (0.52, 0.78), (0.58, 0.78)); _arrow(ax, (0.76, 0.78), (0.82, 0.78))
    _box(ax, (0.20, 0.28), 0.22, 0.18, "Existing direct-WCT OOF\nnot retrained", "#FDE4C7")
    _box(ax, (0.49, 0.28), 0.22, 0.18, "Complete-pathway comparison\nbackgrounds differ", "#FFF0DE")
    _box(ax, (0.78, 0.28), 0.19, 0.18, "Cross-year operational\nstress test\naggregate only", "#E9E3F2")
    _arrow(ax, (0.42, 0.37), (0.49, 0.37)); _arrow(ax, (0.71, 0.37), (0.78, 0.37))
    ax.text(0.5, 0.95, "Corrected microclimate and exposure-evaluation workflow", ha="center", va="top", fontsize=14, fontweight="bold")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.03)
    return _save(fig, output_dir, "Figure_1_workflow", [source], {"mapping": "manuscript Figure 1", "schematic_only": True})


def _extended_3(source_dir: Path, output_dir: Path) -> list[Path]:
    overall_path = source_dir / "main_figure_4_direct_wct_v2.csv"
    month_path = source_dir / "extended_data_figure_3_direct_monthly_v2.csv"
    station_path = source_dir / "extended_data_figure_3_direct_station_distribution_v2.csv"
    overall, month, station = pd.read_csv(overall_path), pd.read_csv(month_path), pd.read_csv(station_path)
    fig, axes = plt.subplots(2, 2, figsize=(9.5, 6.8))
    first_bars = None
    for ax, group, title in zip(axes[0], ["all_stations", "excluding_mismatch"], ["All stations", "Elevation mismatch excluded"]):
        frame = overall[overall.group == group].set_index("variable")
        values = [frame.loc["component_WCT", "background_rmse"], frame.loc["component_WCT", "corrected_rmse"], frame.loc["direct_WCT_own_background", "corrected_rmse"]]
        bars = ax.bar(range(3), values, 0.60, color=[BASELINE, COMPONENT, DIRECT], edgecolor=EDGE, linewidth=0.45)
        first_bars = first_bars or bars
        ax.set_xticks(range(3), ["Component\nbackground", "Component\ncorrected", "Direct\ncorrected"]); ax.set_ylim(0, max(values) * 1.22); ax.set_title(title); _axis(ax); _labels(ax, bars)
    axes[0, 0].set_ylabel("WCT RMSE (°C)")
    for scenario, label, color in [("all_stations", "All stations", COMPONENT), ("excluding_mismatch", "Mismatch excluded", DIRECT)]:
        frame = month[month.scenario == scenario].sort_values("month")
        axes[1, 0].plot(np.arange(len(frame)), frame.direct_minus_component_rmse, marker="o", linewidth=1.7, color=color, label=label)
    axes[1, 0].axhline(0, color=EDGE, linewidth=0.8); axes[1, 0].set_xticks(range(4), ["Jan", "Feb", "Mar", "Apr"]); axes[1, 0].set_ylabel("Direct − component RMSE (°C)"); axes[1, 0].legend(frameon=False); _axis(axes[1, 0], "both")
    arrays = [station.loc[station.scenario == value, "direct_minus_component_rmse"].to_numpy(float) for value in ["all_stations", "excluding_mismatch"]]
    boxplot = axes[1, 1].boxplot(arrays, tick_labels=["All stations", "Mismatch excluded"], widths=0.52, patch_artist=True, showfliers=False)
    for patch, color in zip(boxplot["boxes"], [COMPONENT, DIRECT]): patch.set_facecolor(color); patch.set_alpha(0.7)
    axes[1, 1].axhline(0, color=EDGE, linewidth=0.8); axes[1, 1].set_ylabel("Direct − component RMSE (°C)"); _axis(axes[1, 1])
    for ax, label in zip(axes.ravel(), "abcd"): _panel(ax, label)
    fig.legend([first_bars[0], first_bars[1], first_bars[2]], ["Component pathway background", "Component-corrected", "Direct WCT corrected"], loc="upper center", ncol=3, frameon=False)
    fig.subplots_adjust(top=0.88, bottom=0.14, left=0.10, right=0.98, wspace=0.30, hspace=0.40)
    return _save(fig, output_dir, "Supplementary_Figure_2_direct_heterogeneity", [overall_path, month_path, station_path], {"mapping": "Supplementary Figure 2", "anonymous_station_distribution": True})


def render_all_public_figures(source_dir: str | Path, output_dir: str | Path) -> list[Path]:
    source = Path(source_dir)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    _style()
    generated: list[Path] = []
    renderers: list[Callable[[Path, Path], list[Path]]] = [_extended_2, _figure_1, _figure_2, _figure_3, _figure_4, _extended_3]
    for renderer in renderers:
        generated.extend(renderer(source, output))
    return generated
