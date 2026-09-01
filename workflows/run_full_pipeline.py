#!/usr/bin/env python3
"""Opt-in full component OOF pipeline from authorized prepared inputs only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from wce.pipeline.full import run_full_pipeline


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--execute", action="store_true", help="Required to train or write outputs")
    result.add_argument("--config", required=True)
    result.add_argument("--input-root", required=True)
    result.add_argument("--output-root", required=True)
    return result


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    feature_path = path.parent / config["locked_feature_config"]
    locked = json.loads(feature_path.read_text(encoding="utf-8"))
    for target, target_config in config["targets"].items():
        target_config.update(locked["targets"][target])
    return config


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    if not args.execute:
        print(json.dumps({"status": "DRY_RUN", "scope": config["scope"], "training_run": False, "network_access": False, "external_evaluation": False, "full_grid_generation": False}, sort_keys=True))
        return 0
    manifest = run_full_pipeline(config, args.input_root, args.output_root)
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

