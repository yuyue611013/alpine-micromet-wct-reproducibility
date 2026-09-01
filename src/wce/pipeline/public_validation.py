"""Public-only validation; contains no permission-controlled data access."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from wce.contracts.scientific import ContractError
from wce.metrics.public import verify_public_numeric_contract


def validate_public_repository(repository_root: str | Path) -> dict:
    root = Path(repository_root)
    numeric = verify_public_numeric_contract(root)
    forbidden_extensions = {".nc", ".netcdf", ".parquet", ".npz", ".pkl", ".pickle", ".joblib"}
    prohibited_files = [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.suffix.lower() in forbidden_extensions]
    if prohibited_files:
        raise ContractError(f"PROHIBITED_PUBLIC_FILE:{prohibited_files}")
    unsafe_columns = {"station_id", "station_name", "latitude", "longitude", "provider_id", "site_id", "time_utc"}
    column_findings = []
    for path in list((root / "data").rglob("*.csv")):
        columns = {str(value).lower() for value in pd.read_csv(path, nrows=0).columns}
        if columns & unsafe_columns:
            column_findings.append(path.relative_to(root).as_posix())
    if column_findings:
        raise ContractError(f"IDENTIFYING_OR_ROW_KEY_COLUMNS:{column_findings}")
    return {
        "status": "PASS",
        "numeric_contract": numeric["status"],
        "prohibited_binary_files": 0,
        "identifying_or_row_key_files": 0,
        "permission_controlled_validation": "NOT_INCLUDED_INTERFACE_ONLY",
    }

