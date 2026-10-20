"""Actual Qt input/render, cancellation, bounded repeats and startup measurements."""

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")


def stats(values):
    return dict(
        n=len(values),
        samples=values,
        p95=sorted(values)[math.ceil(len(values) * 0.95) - 1],
        max=max(values),
    )


def main():
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtQuick import QQuickItem
    from PySide6.QtTest import QTest

    import veri_ufku
    from veri_ufku.app import create_application
    from veri_ufku.jobs.manager import rss_bytes

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--startup-runs", type=int, default=20)
    args = parser.parse_args()
    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
    result = dict(
        environment="ENV-24",
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        filesystem=subprocess.check_output(
            ["df", "-T", str(args.output.parent.resolve())], text=True
        ),
        date=datetime.now(UTC).isoformat(),
        backend=os.environ["QT_QPA_PLATFORM"],
        software=True,
        physical_display_latency=False,
        package=str(veri_ufku.__file__),
        input_ms={},
        cancel=[],
        repeated_rss=[],
        page_seconds=[],
        max_tick_ms=0,
        source_unchanged=False,
        minimum_hardware_acceptance=False,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="vu-gui24-", dir=args.output.parent.resolve()
    ) as directory:
        base = Path(directory)
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ["XDG_" + key + "_HOME"] = str(base / key.lower())
        startup = []
        for _ in range(args.startup_runs):
            completed = subprocess.run(
                [sys.executable, "-m", "veri_ufku", "--startup-probe"],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            line = next(
                s
                for s in completed.stdout.splitlines()
                if s.startswith("STARTUP_READY ")
            )
            startup.append(json.loads(line.removeprefix("STARTUP_READY ")))
        result["warm_startup_ms"] = stats([s["ms"] for s in startup])
        cold = []
        for _ in range(5):
            with tempfile.TemporaryDirectory(prefix="vu-cold24-") as fresh:
                env = dict(os.environ, QML_DISABLE_DISK_CACHE="1")
                for key in ("CONFIG", "STATE", "CACHE"):
                    env["XDG_" + key + "_HOME"] = fresh + "/" + key
                completed = subprocess.run(
                    [sys.executable, "-m", "veri_ufku", "--startup-probe"],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=True,
                )
                line = next(
                    s
                    for s in completed.stdout.splitlines()
                    if s.startswith("STARTUP_READY ")
                )
                cold.append(json.loads(line.removeprefix("STARTUP_READY "))["ms"])
        result["fresh_application_cache_startup_ms"] = stats(cold)
        result["cold_startup_ms"] = None  # OS filesystem caches were not dropped.
        result["idle_rss_bytes"] = max(s["rss_bytes"] for s in startup)
        source = base / "source.csv"
        with source.open("w") as stream:
            stream.write("key,x,y,category,note\n")
            for i in range(100000):
                stream.write(
                    f"{i},{i % 997},{(i % 997) * 3 + 7},C{i % 23},Türkçe kayıt ğüşiöç {'uzun not ' * 12}\n"
                )
        original = hashlib.sha256(source.read_bytes()).hexdigest()
        app, window, bridge = create_application()
        engine = app._veri_ufku_resources[0]
        projects, imports, data = (
            engine._projects_resources,
            engine._imports_resources,
            engine._dataset_resources,
        )
        supervisor = engine._resource_supervisor
        last = time.monotonic()

        def tick():
            nonlocal last
            app.processEvents()
            QTest.qWait(5)
            now = time.monotonic()
            result["max_tick_ms"] = max(result["max_tick_ms"], (now - last) * 1000)
            last = now

        def wait(predicate, timeout=180):
            start = time.monotonic()
            while not predicate():
                tick()
                assert time.monotonic() - start < timeout
            return time.monotonic() - start

        def events(name, busy):
            button = window.findChild(QQuickItem, "advancedButton")
            point = button.mapToScene(
                QPointF(button.width() / 2, button.height() / 2)
            ).toPoint()
            values, during = [], 0
            for _ in range(100):
                button = window.findChild(
                    QQuickItem,
                    "beginnerButton"
                    if window.property("advanced")
                    else "advancedButton",
                )
                point = button.mapToScene(
                    QPointF(button.width() / 2, button.height() / 2)
                ).toPoint()
                before = window.property("advanced")
                during += int(busy())
                start = time.monotonic()
                QTest.mouseClick(window, Qt.LeftButton, pos=point)
                wait(lambda: window.property("advanced") != before)
                assert not window.grabWindow().isNull()
                values.append((time.monotonic() - start) * 1000)
                tick()
            result["input_ms"][name] = dict(stats(values), events_while_busy=during)

        try:
            assert projects.create(str(base / "project"))
            last = time.monotonic()
            start = last
            imports.choose(str(source))
            wait(lambda: not imports.busy)
            assert imports.ready, imports.errorText
            result["capture_plus_preview_ms"] = (time.monotonic() - start) * 1000
            result["preview_rows"] = imports.model.rowCount()
            imports.setType(0, "int64")
            imports.refreshPreview()
            wait(lambda: not imports.busy)
            assert imports.ready
            start = time.monotonic()
            imports.importData()
            # Shared admission: demo CPU cannot race with real import.
            bridge.start("demo.cpu")
            assert not bridge._active
            events("import", lambda: imports.busy)
            wait(lambda: not imports.busy)
            assert not imports.errorText, imports.errorText
            result["import_seconds"] = time.monotonic() - start
            data.selectDataset(projects.draft["datasets"][-1]["dataset_id"])
            wait(lambda: not data.busy)
            x = next(
                c["id"]
                for c in data.dataset()["import_metadata"]["columns"]
                if c["name"] == "key"
            )
            data.selectColumn(x)
            start = time.monotonic()
            data.computeProfile(False, "dataset", 1)
            events("profile", lambda: data.busy)
            wait(lambda: not data.busy)
            assert not data.errorText, data.errorText
            assert data.profileResult["used_n"] == 100000
            result["profile_seconds"] = time.monotonic() - start
            for _ in range(24):
                start = time.monotonic()
                data.refresh()
                wait(lambda: not data.busy)
                assert not data.errorText
                result["page_seconds"].append(time.monotonic() - start)
                result["repeated_rss"].append(rss_bytes(os.getpid()))
                assert data.model.rowCount() <= 200
                assert len(data.page_cache.entries) <= 3
            result["page_cache_bytes"] = data.page_cache.bytes
            result["repeated_rss_growth_bytes"] = max(result["repeated_rss"][4:]) - min(
                result["repeated_rss"][4:]
            )
            before = (projects.store.root / "ACTIVE").read_bytes()
            for _ in range(10):
                imports.choose(str(source))
                wait(lambda: not imports.busy)
                imports.importData()
                wait(lambda: "Kayıt doğrulama" in imports.message or not imports.busy)
                assert imports.busy, "Cancellation must reach the parsing stage"
                workspace = Path(imports.workspace)
                start = time.monotonic()
                imports.cancel()
                feedback = (time.monotonic() - start) * 1000
                wait(lambda: not imports.busy)
                elapsed = (time.monotonic() - start) * 1000
                assert not workspace.exists()
                assert before == (projects.store.root / "ACTIVE").read_bytes()
                result["cancel"].append(
                    dict(
                        feedback_ms=feedback,
                        exit_and_cleanup_ms=elapsed,
                        temporary_directory_removed=True,
                    )
                )
            # Real GUI worker: enforce aggregate RAM before publication.
            imports.choose(str(source))
            wait(lambda: not imports.busy)
            imports.importData()
            supervisor.budget = replace(
                supervisor.budget, ram_bytes=rss_bytes(os.getpid()) + 1024 * 1024
            )
            wait(lambda: not imports.busy)
            assert "bellek" in imports.errorText.casefold(), imports.errorText
            assert before == (projects.store.root / "ACTIVE").read_bytes()
            result["ram_limit_error"] = imports.errorText
            result["source_unchanged"] = (
                original == hashlib.sha256(source.read_bytes()).hexdigest()
            )
            result["peak_parent_worker_rss_bytes"] = supervisor.peak_rss_bytes
            result["peak_heavy_processes"] = supervisor.peak_cpu_jobs
            result["peak_shared_scratch_bytes"] = supervisor.peak_temp_bytes
            result["project_staging_entries"] = len(
                list(projects.store.path("staging").iterdir())
            )
            assert result["project_staging_entries"] == 0
            result["cancel_exit_cleanup_ms"] = stats(
                [c["exit_and_cleanup_ms"] for c in result["cancel"]]
            )
            assert result["source_unchanged"] and supervisor.peak_cpu_jobs == 1
            screenshot = args.output.with_suffix(".png")
            window.resize(1366, 768)
            tick()
            assert window.grabWindow().save(str(screenshot))
        finally:
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
