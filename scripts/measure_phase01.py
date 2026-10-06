"""First-frame, actual Qt input, cancellation, RSS and managed scratch measurements."""

import hashlib
import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")


def p95(values):
    return sorted(values)[math.ceil(len(values) * 0.95) - 1]


def main():
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtQuick import QQuickItem
    from PySide6.QtTest import QTest

    from veri_ufku.app import create_application
    from veri_ufku.domain.contracts import DemoParameters, JobSpec

    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="veri-ufku-measure-") as directory:
        for name in ("CONFIG", "STATE", "CACHE"):
            os.environ[f"XDG_{name}_HOME"] = str(Path(directory) / name.lower())
        startup, idle_rss = [], []
        for _ in range(20):
            completed = subprocess.run(
                [sys.executable, "-m", "veri_ufku", "--startup-probe"],
                text=True,
                capture_output=True,
                timeout=15,
                check=True,
            )
            line = next(
                line
                for line in completed.stdout.splitlines()
                if line.startswith("STARTUP_READY ")
            )
            value = json.loads(line.removeprefix("STARTUP_READY "))
            startup.append(value["ms"])
            idle_rss.append(value["rss_bytes"])
        app, window, bridge = create_application()
        manager = bridge.session.manager

        def wait(predicate, timeout=10):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                app.processEvents()
                if predicate():
                    return
                QTest.qWait(5)
            raise RuntimeError("Measurement did not complete")

        try:
            wait(lambda: not window.grabWindow().isNull())
            window.grabWindow().save(str(root / "docs/evidence/phase01-headless.png"))
            bridge.start("demo.cpu")
            cpu_id = bridge.job_id
            io_ids = [
                manager.submit(
                    JobSpec("demo.io", bridge.session.binding, DemoParameters())
                )
                for _ in range(2)
            ]
            wait(
                lambda: all(
                    manager.snapshot(ident).progress.done >= 1
                    for ident in [cpu_id, *io_ids]
                )
            )
            button = window.findChild(QQuickItem, "contextButton")
            point = button.mapToScene(
                QPointF(button.width() / 2, button.height() / 2)
            ).toPoint()
            latency = []
            for _ in range(100):
                before = bridge.revision
                start = time.monotonic()
                QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=point)
                wait(lambda: bridge.revision == before + 1)
                # Wait for a render as well as the Qt input handler.
                window.grabWindow()
                latency.append((time.monotonic() - start) * 1000)
            cancel_start = time.monotonic()
            bridge.cancel()
            feedback_ms = (time.monotonic() - cancel_start) * 1000
            wait(lambda: manager.snapshot(cpu_id).state.terminal)
            stopped_ms = (time.monotonic() - cancel_start) * 1000
            canceled = manager.snapshot(cpu_id)
            wait(
                lambda: all(manager.snapshot(ident).state.terminal for ident in io_ids)
            )
            result = {
                "environment": {
                    "id": "ENV-01",
                    "date": "2026-10-06",
                    "python": platform.python_version(),
                    "platform": platform.platform(),
                    "qt_platform": os.environ["QT_QPA_PLATFORM"],
                    "pyside6": importlib.metadata.version("PySide6"),
                    "lock_sha256": hashlib.sha256(
                        (root / "uv.lock").read_bytes()
                    ).hexdigest(),
                    "script_sha256": hashlib.sha256(
                        Path(__file__).read_bytes()
                    ).hexdigest(),
                    "hardware": "Ryzen 7 8845HS / 32GB / Btrfs; scratch is tmpfs",
                    "target_minimum_hardware": False,
                },
                "warm_first_frame_ms": {
                    "samples": startup,
                    "p95": p95(startup),
                    "max": max(startup),
                },
                "cold_first_frame_ms": None,
                "idle_peak_rss_bytes": max(idle_rss),
                "input_to_render_ms": {
                    "samples": latency,
                    "p95": p95(latency),
                    "max": max(latency),
                    "events": len(latency),
                },
                "cancel": {
                    "samples": 1,
                    "feedback_ms": feedback_ms,
                    "worker_exit_and_cleanup_ms": stopped_ms,
                    "worker_timestamp_ms": (
                        canceled.ended_at - canceled.cancel_requested_at
                    )
                    * 1000,
                    "state": canceled.state.value,
                    "result_published": canceled.result is not None,
                },
                "peak_total_rss_bytes": manager.peak_rss_bytes,
                "peak_managed_temp_bytes": manager.peak_temp_bytes,
                "peak_cpu_jobs": manager.peak_cpu_jobs,
                "peak_io_jobs": manager.peak_io_jobs,
                "leftover_job_workspaces": len(
                    list((manager.cache / "jobs").glob("job-*"))
                ),
                "desktop_test": False,
            }
            path = root / "docs/evidence/phase01-measurements.json"
            path.write_text(json.dumps(result, indent=2) + "\n")
            print(
                json.dumps(
                    {
                        k: v
                        for k, v in result.items()
                        if k not in {"warm_first_frame_ms", "input_to_render_ms"}
                    },
                    indent=2,
                )
            )
            print("startup p95 ms", p95(startup), "input/render p95 ms", p95(latency))
        finally:
            manager.shutdown()
            app._veri_ufku_resources[-1]()
            window.hide()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
