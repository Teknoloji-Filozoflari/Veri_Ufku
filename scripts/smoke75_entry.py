"""Isolated installed-wheel entry smoke; never inherits user application settings."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="vu-f75-entry-") as folder:
        env = os.environ.copy()
        for key in ("CONFIG", "STATE", "CACHE", "DATA"):
            env["XDG_" + key + "_HOME"] = str(Path(folder) / key.lower())
        env.update(
            PYTHONPATH=str(a.package_root.resolve()),
            QT_QPA_PLATFORM="offscreen",
            QT_QUICK_BACKEND="software",
        )
        command = [sys.executable, "-m", "veri_ufku", "--smoke-test"]
        try:
            result = subprocess.run(
                command, env=env, cwd="/tmp", capture_output=True, text=True, timeout=45
            )
            value = dict(
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                isolated_XDG=True,
                budget="default2GiB",
                scope="Actual QML/CPU435 entry; not all modules or human test",
            )
        except subprocess.TimeoutExpired:
            value = dict(
                command=command,
                exit_code=124,
                status="timeout-not-success",
                isolated_XDG=True,
                budget="default2GiB",
            )
        a.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        raise SystemExit(value["exit_code"])


if __name__ == "__main__":
    main()
