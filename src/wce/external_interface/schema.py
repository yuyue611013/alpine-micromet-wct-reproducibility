"""Schema-only external interface with no real data paths or identities."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from wce.contracts.scientific import ContractError


def validate_synthetic_external_schema(frame: pd.DataFrame, schema_path: str | Path) -> dict:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    required = {item["name"] for item in schema["synthetic_input_fields"]}
    if set(frame.columns) != required:
        raise ContractError(f"EXTERNAL_SCHEMA_MISMATCH:{sorted(required - set(frame.columns))}")
    if schema.get("public_repository_contains_real_rows") is not False or schema.get("permission_required") is not True:
        raise ContractError("EXTERNAL_PERMISSION_CONTRACT_CHANGED")
    return {
        "status": "PASS",
        "design_label": schema["design_label"],
        "real_endpoint_executable": False,
        "permission_required": True,
    }

