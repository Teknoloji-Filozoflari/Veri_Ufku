"""Actual monitoring desktop walkthrough; optional noneditable package."""

import argparse
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--only", default="")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    sys.path.insert(1, str(root / "tests"))
    args.output.mkdir(parents=True, exist_ok=True)
    import pytest
    import test_monitoring_gui as cases
    from PySide6.QtCore import QObject, QPointF
    from PySide6.QtTest import QTest

    import veri_ufku
    from veri_ufku.modeling.monitoring import public_report

    package = Path(veri_ufku.__file__).resolve()
    if args.package_root:
        assert package.is_relative_to(args.package_root.resolve())
    records = []

    def capture(app, window, projects, controller, task):
        window.setProperty("selectedSection", 5)
        window.findChild(QObject, "monitoringExpanded").setProperty("checked", True)
        record = dict(
            task=task,
            report=public_report(controller.result),
            route=controller.currentRoute,
            ram_budget_bytes=controller.budget.ram_bytes,
            peak_rss_bytes=app._veri_ufku_resources[
                0
            ]._resource_supervisor.peak_rss_bytes,
        )
        target = window.findChild(QObject, "monitoringReport")
        for width, height in ((1000, 740), (1366, 900)):
            window.setWidth(width)
            window.setHeight(height)
            app.processEvents()
            QTest.qWait(250)
            parent = target.parentItem()
            while parent:
                if parent.property("contentY") is not None:
                    pos = target.mapToItem(parent.property("contentItem"), 0, 0)
                    parent.setProperty("contentY", max(0, pos.y() - 20))
                parent = parent.parentItem()
            QTest.qWait(200)
            app.processEvents()
            position = target.mapToScene(QPointF(0, 0))
            assert (
                target.property("visible")
                and position.y() < height
                and position.y() + target.height() > 0
            )
            assert window.grabWindow().save(str(args.output / f"{task}-{width}.png"))
        records.append(record)

    cases.CAPTURE = capture
    cmd = [
        "-q",
        str(root / "tests/test_monitoring_gui.py"),
        "--junitxml=" + str(args.output / "gui.xml"),
    ]
    if args.only:
        cmd += ["-k", args.only]
    result = pytest.main(cmd)
    value = dict(
        at=datetime.now(UTC).isoformat(),
        package=str(package),
        python=platform.python_version(),
        platform=platform.platform(),
        cpu=next(
            (
                line.split(":", 1)[1].strip()
                for line in Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")
            ),
            "unknown",
        ),
        affinity=len(os.sched_getaffinity(0)),
        pytest_exit=result,
        records=records,
        scope="offscreen actual GUI; drift2GiB/model shadow explicit4GiB; physical/human/AT separate",
    )
    (args.output / "measurement.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
