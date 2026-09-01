"""Portable, root-scoped and non-clobbering I/O helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .scientific import ContractError


def resolve_within(root: str | Path, value: str | Path) -> Path:
    base = Path(root).resolve()
    candidate = Path(value)
    candidate = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
    if candidate != base and base not in candidate.parents:
        raise ContractError("PATH_ESCAPES_DECLARED_ROOT")
    return candidate


def require_absent(path: str | Path) -> Path:
    target = Path(path)
    if target.exists():
        raise ContractError(f"NON_CLOBBER:{target}")
    return target


def write_json_once(path: str | Path, payload: Any) -> Path:
    target = require_absent(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return target


def write_text_once(path: str | Path, text: str) -> Path:
    target = require_absent(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

