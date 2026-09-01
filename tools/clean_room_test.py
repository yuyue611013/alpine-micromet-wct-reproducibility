#!/usr/bin/env python3
"""Run the complete public route from an isolated temporary repository copy with network blocked."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repository-root", default=".")
    return result


def run(command: list[str], cwd: Path, environment: dict[str, str]) -> dict:
    completed = subprocess.run(command, cwd=cwd, env=environment, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"CLEAN_ROOM_COMMAND_FAILED:{command}:{completed.stdout}:{completed.stderr}")
    return {"command": command[1:], "returncode": completed.returncode, "stdout_tail": completed.stdout.strip().splitlines()[-1:]}


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    source = Path(args.repository_root).resolve()
    with tempfile.TemporaryDirectory(prefix="wce_clean_room_") as temporary:
        temporary_root = Path(temporary)
        repository = temporary_root / "repository"
        shutil.copytree(
            source,
            repository,
            ignore=shutil.ignore_patterns(".git", ".DS_Store", "__pycache__", "*.pyc", "reproduced_outputs", "*.egg-info"),
        )
        guard = temporary_root / "guard"
        guard.mkdir()
        (guard / "sitecustomize.py").write_text(
            "import socket\n"
            "def _blocked(*args, **kwargs):\n    raise RuntimeError('NETWORK_DISABLED_IN_CLEAN_ROOM')\n"
            "socket.create_connection = _blocked\n"
            "_original = socket.socket\n"
            "class GuardedSocket(_original):\n    def connect(self, *args, **kwargs):\n        return _blocked(*args, **kwargs)\n"
            "socket.socket = GuardedSocket\n",
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONPATH"] = os.pathsep.join([str(guard), str(repository / "src")])
        environment["MPLCONFIGDIR"] = str(temporary_root / "mpl-cache")
        environment["NO_PROXY"] = "*"
        python = sys.executable
        commands = [
            [python, "-B", "workflows/validate_installation.py"],
            [python, "-B", "workflows/reproduce_public_results.py", "--output-root", "reproduced_outputs"],
            [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
            [python, "-B", "tools/security_scan.py", "--root", "."],
            [python, "-B", "tools/verify_reference_outputs.py"],
        ]
        results = [run(command, repository, environment) for command in commands]
        output_manifest = json.loads((repository / "reproduced_outputs/public_reproduction_manifest.json").read_text(encoding="utf-8"))
        if output_manifest.get("status") != "PASS" or output_manifest.get("repository_internal_inputs_only") is not True:
            raise RuntimeError("CLEAN_ROOM_PUBLIC_MANIFEST_FAILED")
        if any(path.is_symlink() for path in repository.rglob("*")):
            raise RuntimeError("CLEAN_ROOM_SYMLINK_FOUND")
        print(json.dumps({
            "status": "PASS",
            "filesystem_isolated": True,
            "network_disabled": True,
            "repository_internal_public_inputs_only": True,
            "dependency_environment": "CALLER_PREINSTALLED_NOT_RECREATED",
            "original_project_read": False,
            "commands": results,
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
