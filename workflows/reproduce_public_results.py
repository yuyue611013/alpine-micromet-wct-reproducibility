#!/usr/bin/env python3
"""Default aggregate-only public reproduction entrypoint."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from wce.contracts.io import require_absent, sha256_file, write_json_once
from wce.metrics.public import verify_public_numeric_contract
from wce.pipeline.public_validation import validate_public_repository
from wce.plotting.public_figures import render_all_public_figures


ROOT = Path(__file__).resolve().parents[1]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output-root", default="reproduced_outputs")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    output = Path(args.output_root)
    if not output.is_absolute():
        output = ROOT / output
    require_absent(output)
    public_validation = validate_public_repository(ROOT)
    numeric = verify_public_numeric_contract(ROOT)
    output.mkdir(parents=True, exist_ok=False)
    tables = output / "tables"
    tables.mkdir()
    copy_map = {
        ROOT / "reference_outputs/tables/core_result_table_source_v1.csv": tables / "manuscript_core_results.csv",
        ROOT / "data/aggregate/component_metrics_overall_v1.csv": tables / "component_metrics_overall.csv",
        ROOT / "data/aggregate/component_metrics_monthly_v1.csv": tables / "supplementary_monthly_metrics.csv",
        ROOT / "data/aggregate/component_metrics_groups_v1.csv": tables / "supplementary_representativeness_groups.csv",
        ROOT / "data/aggregate/direct_wct_comparison_v1.csv": tables / "supplementary_direct_wct_comparison.csv",
        ROOT / "data/aggregate/external_aggregate_metrics_v1.csv": tables / "external_cross_year_aggregate_metrics.csv",
    }
    for source, destination in copy_map.items():
        shutil.copyfile(source, destination)
    figures = render_all_public_figures(ROOT / "data/figure_source", output / "figures")
    write_json_once(output / "numeric_verification_report.json", numeric)
    generated = sorted(path for path in output.rglob("*") if path.is_file())
    write_json_once(
        output / "public_reproduction_manifest.json",
        {
            "status": "PASS",
            "scope": "PUBLIC_RESULT_REPRODUCTION",
            "repository_internal_inputs_only": True,
            "numeric_verification": numeric["status"],
            "public_validation": public_validation["status"],
            "figure_files": len(figures),
            "files": [{"relative_path": path.relative_to(output).as_posix(), "sha256": sha256_file(path)} for path in generated],
        },
    )
    print("PUBLIC_REPRODUCTION_STATUS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

