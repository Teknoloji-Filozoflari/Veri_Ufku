"""Actual bounded Phase65 GUI routes; isolated XDG, optional installed package."""

import argparse
import hashlib
import json
import os
import platform
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--only", default="")
    parser.add_argument("--view", choices=("result", "editor"), default="result")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    sys.path.insert(1, str(root / "tests"))
    import pytest
    import test_repro_gui as cases
    from PySide6.QtCore import QObject, QPointF
    from PySide6.QtTest import QTest

    import veri_ufku

    package = Path(veri_ufku.__file__).resolve()
    if args.package_root:
        assert package.is_relative_to(args.package_root.resolve()), package
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    records = []

    def capture(app, window, projects, controller, task):
        active = dict(
            result=controller.result,
            preview=controller.preview_result,
            opened=controller.opened,
            graph=controller.graph_result,
        )
        record = dict(
            task=task,
            status=controller.result.get("status")
            or controller.result.get("comparison", {}).get("status")
            or ("error" if controller.errorText else "metadata"),
            ui_pid=os.getpid(),
            error=controller.errorText,
            graph_nodes=len(controller.graph_result.get("nodes", [])),
            view=args.view,
            focus=controller.selected,
            budget=asdict(controller.budget),
            peak_rss_bytes=app._veri_ufku_resources[
                0
            ]._resource_supervisor.peak_rss_bytes,
        )
        (output / (task + ".json")).write_text(
            json.dumps(active, ensure_ascii=False, indent=2)
        )
        if args.view == "editor":
            panel = window.findChild(QObject, "reproPanel")
            canvas = next(
                obj
                for obj in panel.findChildren(QObject)
                if "Canvas" in obj.metaObject().className()
            )
            target = canvas.parentItem()
        else:
            target = window.findChild(
                QObject,
                "reproResultCaption"
                if task in ("report-reference", "model-numeric")
                else "reproStatusCaption",
            )
        for width, height in ((1000, 740), (1366, 900)):
            window.setWidth(width)
            window.setHeight(height)
            window.findChild(QObject, "reproExpanded").setProperty("checked", True)
            app.processEvents()
            QTest.qWait(250)
            app.processEvents()
            parent = target.parentItem()
            while parent:
                if parent.property("contentY") is not None:
                    pos = target.mapToItem(parent.property("contentItem"), 0, 0)
                    parent.setProperty("contentY", max(0, pos.y() - 10))
                    break
                parent = parent.parentItem()
            for _ in range(3):
                QTest.qWait(100)
                app.processEvents()
                if parent:
                    pos = target.mapToItem(parent.property("contentItem"), 0, 0)
                    parent.setProperty("contentY", max(0, pos.y() - 10))
            QTest.qWait(150)
            app.processEvents()
            location = target.mapToScene(QPointF(0, 0))
            record.setdefault("captions", []).append(
                dict(
                    width=width,
                    y=location.y(),
                    visible=target.property("visible"),
                    text=target.property("text"),
                )
            )
            assert target.property("visible") and 0 <= location.y() < height - 30, (
                record["captions"][-1]
            )
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
            str(root / "tests/test_repro_gui.py"),
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
