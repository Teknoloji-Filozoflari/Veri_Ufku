"""Actual bounded Phase61 GUI routes; isolated XDG, optional installed package."""

import argparse
import hashlib
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--only", default="")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    sys.path.insert(1, str(root / "tests"))
    import pytest
    import test_graphs_gui as cases
    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest

    import veri_ufku

    package = Path(veri_ufku.__file__).resolve()
    if args.package_root:
        assert package.is_relative_to(args.package_root.resolve()), package
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    records = []

    def capture(app, window, projects, controller, task):
        record = dict(
            task=task,
            status=controller.active["status"],
            worker_pid=controller.active.get("worker_pid"),
            ui_pid=os.getpid(),
            metrics=controller.active["metrics"],
            source_snapshot_id=controller.active["source_snapshot_id"],
            prior_test_use_ids=controller.active["prior_test_use_ids"],
            saved=controller.saved(),
        )
        (output / (task + ".json")).write_text(
            json.dumps(controller.active, ensure_ascii=False, indent=2, allow_nan=False)
        )
        target = window.findChild(QObject, "graphSummary")
        for width, height in ((1000, 740), (1366, 900)):
            window.setWidth(width)
            window.setHeight(height)
            target.forceActiveFocus()
            parent = target.parentItem()
            while parent:
                if parent.property("contentY") is not None:
                    pos = target.mapToItem(parent.property("contentItem"), 0, 0)
                    parent.setProperty("contentY", max(0, pos.y() - 10))
                    break
                parent = parent.parentItem()
            QTest.qWait(150)
            app.processEvents()
            path = output / f"{task}-{width}.png"
            assert window.grabWindow().save(str(path))
        record["screenshots"] = [
            str(output / f"{task}-{width}.png") for width in (1000, 1366)
        ]
        records.append(record)

    cases.CAPTURE = capture
    code = pytest.main(
        [
            "-q",
            str(root / "tests/test_graphs_gui.py"),
            "--disable-warnings",
            *(["-k", args.only] if args.only else []),
            "--junitxml=" + str(output / "gui.xml"),
        ]
    )
    hashes = {
        str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in output.iterdir()
        if p.is_file()
    }
    (output / "walkthrough.json").write_text(
        json.dumps(
            dict(
                date=datetime.now(UTC).isoformat(),
                python=platform.python_version(),
                platform=platform.platform(),
                package=str(package),
                qt_platform=os.environ.get("QT_QPA_PLATFORM"),
                exit_code=code,
                records=records,
                artifacts=hashes,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
