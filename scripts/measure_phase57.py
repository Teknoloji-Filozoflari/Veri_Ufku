"""Actual source/installed local vision GUI, synthetic immutable evidence only."""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--case",
        choices=(
            "scan",
            "classification",
            "transfer",
            "detection",
            "segmentation",
            "review-export-cancel",
        ),
    )
    args = parser.parse_args()
    package = args.package_root or ROOT / "src"
    sys.path.insert(0, str(package))
    sys.path.insert(1, str(ROOT / "tests"))
    os.environ.update(
        PYTHONPATH=str(package),
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
    )
    import pytest
    import test_vision_gui as cases
    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest

    import veri_ufku

    assert Path(veri_ufku.__file__).is_relative_to(package)
    args.output.mkdir(parents=True, exist_ok=True)
    records = []

    def capture(app, window, projects, controller, task):
        folder = args.output / task
        folder.mkdir(exist_ok=True)
        files = []
        for name, value in (
            ("run", controller.summary(controller.active)),
            ("prediction", controller.predictionReport),
        ):
            path = folder / (name + ".json")
            path.write_text(
                json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
            )
            files.append(path)
        for width in (1000, 1366):
            window.setWidth(width)
            QTest.qWait(150)
            item = window.findChild(QObject, "visionSummary")
            item.forceActiveFocus()
            parent = item.parentItem()
            while parent is not None:
                if parent.property("contentY") is not None:
                    position = item.mapToItem(parent.property("contentItem"), 0, 0)
                    parent.setProperty("contentY", max(0, position.y() - 20))
                    break
                parent = parent.parentItem()
            QTest.qWait(150)
            path = folder / f"vision-{width}.png"
            assert window.grabWindow().save(str(path))
            files.append(path)
        records.append(
            dict(
                task=task,
                status="passed",
                run_id=controller.active["run_id"],
                training_status=controller.active["status"],
                budget_ram_bytes=controller.budget.ram_bytes,
                peak_rss_bytes=app._veri_ufku_resources[
                    0
                ]._resource_supervisor.peak_rss_bytes,
                files=[
                    dict(
                        path=str(p.relative_to(args.output)),
                        sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                    )
                    for p in files
                ],
            )
        )

    cases.CAPTURE = capture
    for task in (
        "scan",
        "classification",
        "transfer",
        "detection",
        "segmentation",
        "review-export-cancel",
    ):
        if args.case and args.case != task:
            continue
        with tempfile.TemporaryDirectory(prefix="veri-ufku-f57-") as td:
            patch = pytest.MonkeyPatch()
            try:
                if task == "review-export-cancel":
                    cases.test_real_gui_review_export_and_cancel(Path(td), patch)
                else:
                    cases.test_real_gui_task_reopen_and_new_data(Path(td), patch, task)
            finally:
                patch.undo()
        print("PASS", task, flush=True)
    (args.output / "walkthrough.json").write_text(
        json.dumps(
            dict(
                id="E57-GUI",
                date=datetime.now(UTC).isoformat(),
                package_root=str(package),
                python=sys.version,
                cases=records,
                limits="Synthetic developer offscreen/software; not human/AT/minimum hardware/physical desktop/offline installer/GPU/general YOLO-U-Net evidence",
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
