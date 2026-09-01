#!/usr/bin/env python3
"""Verify public aggregate values and immutable reference-output hashes."""

from __future__ import annotations

import json
import math
from typing import Any
from pathlib import Path

from wce.metrics.public import collect_public_numeric_values, verify_public_numeric_contract


ROOT = Path(__file__).resolve().parents[1]


def assert_full_precision_close(expected: Any, actual: Any, path: str = "root") -> None:
    """Require identical structure and finite numeric values within the locked tolerance."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(expected) != set(actual):
            raise RuntimeError(f"REFERENCE_STRUCTURE_MISMATCH:{path}")
        for key in sorted(expected):
            assert_full_precision_close(expected[key], actual[key], f"{path}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise RuntimeError(f"REFERENCE_ARRAY_LENGTH_MISMATCH:{path}")
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            assert_full_precision_close(expected_item, actual_item, f"{path}[{index}]")
        return
    if isinstance(expected, bool) or isinstance(actual, bool):
        if expected is not actual:
            raise RuntimeError(f"REFERENCE_VALUE_MISMATCH:{path}")
        return
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        expected_number, actual_number = float(expected), float(actual)
        if not (math.isfinite(expected_number) and math.isfinite(actual_number)):
            raise RuntimeError(f"REFERENCE_NONFINITE_VALUE:{path}")
        if not math.isclose(expected_number, actual_number, rel_tol=1e-12, abs_tol=1e-12):
            raise RuntimeError(f"REFERENCE_NUMERIC_MISMATCH:{path}")
        return
    if type(expected) is not type(actual) or expected != actual:
        raise RuntimeError(f"REFERENCE_VALUE_MISMATCH:{path}")


def main() -> int:
    verification = verify_public_numeric_contract(ROOT)
    reference = json.loads((ROOT / "reference_outputs/metrics/public_numeric_reference_v1.json").read_text(encoding="utf-8"))
    actual = collect_public_numeric_values(ROOT)
    assert_full_precision_close(reference["actual_full_precision"], actual)
    print(json.dumps({"status": "PASS", "numeric_contract": verification["status"], "reference_full_precision": "PASS_TOLERANCE_SAFE", "rtol": 1e-12, "atol": 1e-12}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
