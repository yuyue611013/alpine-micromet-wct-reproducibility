#!/usr/bin/env python3
"""Fail on private paths, sensitive data shapes, prohibited binaries or oversized files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


MAX_BYTES = 50 * 1024 * 1024
PROHIBITED_SUFFIXES = {".nc", ".netcdf", ".parquet", ".npz", ".pkl", ".pickle", ".joblib"}
PROHIBITED_EXACT_NAMES = {".env", ".cdsapirc", "model" + ".txt"}
UNSAFE_DATA_COLUMNS = {
    "station_id", "station_name", "latitude", "longitude", "provider_id", "site_id",
    "venue_name", "station_hour", "row_level_observation",
}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", default=".")
    return result


def findings(root: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    private_user_prefix = "/" + "Users" + "/"
    private_cache_prefix = "/" + "private" + "/" + "tmp" + "/"
    provider_brand = "weather" + "xm"
    legacy_markers = ["outputs/" + "poc2", "outputs/" + "revision_", "releases/" + "phase"]
    credential_words = "(?:" + "|".join(["api_" + "key", "access_" + "token", "password", "client_" + "secret"]) + ")"
    credential_assignment = re.compile(credential_words + r"\s*[:=]\s*['\"][^'\"]{8,}['\"]", re.IGNORECASE)
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if any(part in {".git", "__pycache__"} for part in path.parts):
            issues.append({"path": relative, "reason": "cache_or_git_metadata"})
            continue
        if path.is_symlink():
            issues.append({"path": relative, "reason": "symlink_not_allowed"})
            continue
        if not path.is_file():
            continue
        if path.name in PROHIBITED_EXACT_NAMES or path.name.startswith(".env."):
            issues.append({"path": relative, "reason": "credential_or_model_filename"})
        if path.suffix.lower() in PROHIBITED_SUFFIXES:
            issues.append({"path": relative, "reason": "prohibited_binary_extension"})
        if path.stat().st_size > MAX_BYTES:
            issues.append({"path": relative, "reason": "file_exceeds_50_mb"})
        if any(part.lower() == "restricted" for part in path.parts):
            issues.append({"path": relative, "reason": "permission_controlled_directory"})
        if provider_brand in relative.lower():
            issues.append({"path": relative, "reason": "provider_identifier_in_path"})
        if path.suffix.lower() == ".csv" and ("data/" in relative or "reference_outputs/" in relative):
            columns = {str(value).lower() for value in pd.read_csv(path, nrows=0).columns}
            if columns & UNSAFE_DATA_COLUMNS or ({"station_id", "time_utc"} <= columns):
                issues.append({"path": relative, "reason": "identifying_or_row_level_columns"})
        if path.suffix.lower() in {".py", ".toml", ".yml", ".yaml", ".json", ".md", ".txt", ".cff", ""}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if private_user_prefix in text or private_cache_prefix in text:
                issues.append({"path": relative, "reason": "private_absolute_path"})
            if credential_assignment.search(text):
                issues.append({"path": relative, "reason": "credential_assignment"})
            if path.suffix.lower() in {".py", ".json", ".toml", ".yml", ".yaml"} and any(marker in text for marker in legacy_markers):
                issues.append({"path": relative, "reason": "legacy_result_path_in_executable_or_config"})
    return issues


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.root).resolve()
    issues = findings(root)
    result = {
        "status": "PASS" if not issues else "FAIL",
        "files_scanned": sum(1 for path in root.rglob("*") if path.is_file()),
        "private_absolute_paths": sum(item["reason"] == "private_absolute_path" for item in issues),
        "restricted_files": sum(item["reason"] == "permission_controlled_directory" for item in issues),
        "row_level_files": sum(item["reason"] == "identifying_or_row_level_columns" for item in issues),
        "prohibited_binary_or_model_files": sum(item["reason"] in {"prohibited_binary_extension", "credential_or_model_filename"} for item in issues),
        "issues": issues,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())

