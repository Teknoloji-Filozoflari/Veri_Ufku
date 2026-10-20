"""Run explicit synthetic source/wheel groups in separate bounded processes."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from benchmark75_plan import GROUPS, GUI

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--group", action="append")
    p.add_argument("--kind", choices=("compute", "gui"), default="compute")
    p.add_argument("--package-root", type=Path)
    p.add_argument("--timeout", type=int, default=360)
    p.add_argument("--ram-gib", type=int, choices=(2, 4), default=2)
    a = p.parse_args()
    groups = GROUPS if a.kind == "compute" else GUI
    a.output.mkdir(parents=True, exist_ok=True)
    if a.timeout < 1 or a.timeout > 900:
        p.error("timeout1..900")
    summary = dict(
        recorded_at=datetime.now(UTC).isoformat(),
        python=platform.python_version(),
        platform=platform.platform(),
        kind=a.kind,
        package_root=str(a.package_root) if a.package_root else "source",
        cases=[],
        lock_sha256=hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
        scope="synthetic bounded developer validation; not novice/expert/physical/AT/minimum hardware/whole release acceptance",
    )
    for g in a.group or groups:
        if g not in groups:
            p.error("unknown group " + g)
        folder = a.output / g
        folder.mkdir(exist_ok=False)
        env = os.environ.copy()
        env.update(
            QT_QPA_PLATFORM="offscreen",
            QT_QUICK_BACKEND="software",
            VU75_EVIDENCE=str((folder / "fixtures.json").resolve()),
        )
        if a.kind == "gui":
            env["VU75_GUI_CAPTURE"] = "1"
            env["VU75_GUI_RAM_GIB"] = str(a.ram_gib)
        env["PYTHONPATH"] = os.pathsep.join(
            [
                str(a.package_root.resolve()) if a.package_root else str(ROOT / "src"),
                str(ROOT / "scripts"),
            ]
        )
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "benchmark75_evidence",
            "-o",
            "junit_family=legacy",
            "-o",
            "faulthandler_timeout=120",
            *[str(ROOT / "tests" / n) for n in groups[g]],
            "--junitxml=" + str((folder / "tests.xml").resolve()),
        ]
        start = time.monotonic()
        print(g, "START", flush=True)
        status = "not-run"
        with (folder / "pytest.log").open("w") as out:
            process = subprocess.Popen(
                command,
                env=env,
                cwd="/tmp",
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                code = process.wait(timeout=a.timeout)
                status = "passed" if code == 0 else "failed"
            except subprocess.TimeoutExpired:
                import signal

                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                code = 124
                status = "timeout-not-success"
        summary["cases"].append(
            dict(
                group=g,
                exit_code=code,
                status=status,
                seconds=time.monotonic() - start,
                command=command,
                log=str(folder / "pytest.log"),
            )
        )
        (a.output / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
        )
        print(g, status, round(time.monotonic() - start, 2), flush=True)
    raise SystemExit(0 if all(c["exit_code"] == 0 for c in summary["cases"]) else 1)


if __name__ == "__main__":
    main()
