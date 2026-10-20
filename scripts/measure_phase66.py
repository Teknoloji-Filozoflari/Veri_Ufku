"""Hardware-labelled bounded benchmark; actual GUI panel, optional local Dask."""

import argparse
import json
import os
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--dask", action="store_true")
    parser.add_argument(
        "--search-4gib",
        action="store_true",
        help="Explicit test budget; does not change production default",
    )
    parser.add_argument(
        "--bounded-search-4gib",
        action="store_true",
        help="One-candidate GUI fixture, explicit 4GiB; no curves",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    sys.path.insert(1, str(root / "tests"))
    args.output.mkdir(parents=True, exist_ok=True)
    import veri_ufku
    from veri_ufku.jobs.resources import rss_bytes

    package = Path(veri_ufku.__file__).resolve()
    if args.package_root:
        assert package.is_relative_to(args.package_root.resolve())
    cpu = next(
        (
            line.split(":", 1)[1].strip()
            for line in Path("/proc/cpuinfo").read_text().splitlines()
            if line.startswith("model name")
        ),
        "unknown",
    )
    report = dict(
        at=datetime.now(UTC).isoformat(),
        python=platform.python_version(),
        platform=platform.platform(),
        cpu=cpu,
        affinity_cpus=len(os.sched_getaffinity(0)),
        memory=Path("/proc/meminfo").read_text().splitlines()[0],
        package=str(package),
        claim="Single-machine bounded fixture; no speedup, minimum-hardware or distributed performance claim",
    )
    if args.dask:
        import tempfile

        import pyarrow as pa
        import pyarrow.parquet as pq

        from veri_ufku.importers.delimited import Control
        from veri_ufku.jobs.dask_backend import parquet_summary

        with tempfile.TemporaryDirectory(prefix="f66-bench-") as directory:
            path = Path(directory) / "fixture.parquet"
            pq.write_table(pa.table({"value": list(range(100_000))}), path)
            started = time.monotonic()
            result = parquet_summary(path, "value", Control(), chunk_rows=4096)
            report["dask"] = dict(
                seconds=time.monotonic() - started,
                rss_bytes=rss_bytes(os.getpid()),
                **result,
            )
            assert result["total"] == 100000 * 99999 / 2 and result["n"] == 100000
    else:
        import pytest
        import test_compute_budget_gui as cases

        node = str(root / "tests/test_compute_budget_gui.py")
        if args.bounded_search_4gib:
            node += "::test_real_bounded_search_measurement"
        else:
            node += "::test_real_profile_measurement_panel"
        if args.search_4gib:
            import test_search_gui as cases

            original = cases.imported

            def imported(tmp_path, monkeypatch, *items, **kwargs):
                config = tmp_path / "config/veri_ufku"
                config.mkdir(parents=True, exist_ok=True)
                (config / "settings.json").write_text(
                    json.dumps({"budget": {"ram_bytes": 4 * 1024**3}})
                )
                return original(tmp_path, monkeypatch, *items, **kwargs)

            cases.imported = imported
            original_spin = cases.spin

            def spin(app, predicate, timeout=20000):
                return original_spin(app, predicate, timeout=max(timeout, 150000))

            cases.spin = spin
            report["test_wait_seconds"] = 150
            report["search_wall_budget_seconds"] = 120
            node = (
                str(root / "tests/test_search_gui.py")
                + "::test_real_search_controls_and_model_handoff[grid-independent-regression]"
            )
        from PySide6.QtTest import QTest

        def capture(app, window, *items):
            supervisor = app._veri_ufku_resources[0]._resource_supervisor
            report["explicit_test_ram_bytes"] = supervisor.budget.ram_bytes
            app.processEvents()
            QTest.qWait(200)
            supervisor.poll()
            report["resources"] = supervisor.report
            for width, height in ((1000, 740), (1366, 900)):
                window.setWidth(width)
                window.setHeight(height)
                QTest.qWait(150)
                app.processEvents()
                assert window.grabWindow().save(str(args.output / f"panel-{width}.png"))

        cases.CAPTURE = capture
        status = pytest.main(["-q", node, "--junitxml=" + str(args.output / "gui.xml")])
        report["pytest_exit"] = status
        (args.output / "measurement.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )
        if status:
            raise SystemExit(status)
    (args.output / "measurement.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
