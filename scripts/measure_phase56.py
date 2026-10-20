"""Actual source/noneditable CPU neural GUI paths and safe synthetic evidence."""

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
    parser.add_argument(
        "--case",
        choices=(
            "mlp-regression",
            "mlp-classification",
            "cnn-classification",
            "pause-resume-cancel",
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = args.package_root or ROOT / "src"
    sys.path.insert(0, str(package))
    sys.path.insert(1, str(ROOT / "tests"))
    os.environ.update(
        PYTHONPATH=str(package),
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
    )
    import veri_ufku

    assert Path(veri_ufku.__file__).is_relative_to(package)
    import pytest
    import test_neural_gui as cases
    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest

    args.output.mkdir(parents=True, exist_ok=True)
    records = []

    def capture(app, window, projects, c, template, classification):
        name = template + ("-classification" if classification else "-regression")
        folder = args.output / name
        folder.mkdir(exist_ok=True)
        value = c.summary(c.active)
        run = folder / "run.json"
        run.write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        )
        prediction = folder / "prediction.json"
        prediction.write_text(
            json.dumps(
                c.predictionReport, ensure_ascii=False, allow_nan=False, indent=2
            )
            + "\n"
        )
        files = []
        for width in (1000, 1366):
            window.setWidth(width)
            QTest.qWait(150)
            item = window.findChild(QObject, "neuralSummary")
            window.findChild(QObject, "neuralCurves").forceActiveFocus()
            parent = item.parentItem()
            while parent is not None:
                if parent.property("contentY") is not None:
                    position = item.mapToItem(parent.property("contentItem"), 0, 0)
                    parent.setProperty("contentY", max(0, position.y() - 20))
                    break
                parent = parent.parentItem()
            QTest.qWait(100)
            path = folder / f"neural-{width}.png"
            assert window.grabWindow().save(str(path))
            files.append(path)
        files.extend((run, prediction))
        records.append(
            dict(
                template=template,
                purpose="classification" if classification else "regression",
                status="passed",
                training_status=value["status"],
                epochs=value["epoch"],
                run_id=value["run_id"],
                budget_ram_bytes=c.budget.ram_bytes,
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
    for template, classification in (
        ("mlp", False),
        ("mlp", True),
        ("cnn", True),
        ("pause-resume-cancel", False),
    ):
        name = (
            template
            if template == "pause-resume-cancel"
            else template + ("-classification" if classification else "-regression")
        )
        if args.case and args.case != name:
            continue
        with tempfile.TemporaryDirectory(prefix="veri-ufku-f56-") as td:
            patch = pytest.MonkeyPatch()
            try:
                if template == "pause-resume-cancel":
                    cases.test_real_gui_pause_resume_and_cancel(Path(td), patch)
                else:
                    cases.test_real_gui_training_reopen_new_data_prediction(
                        Path(td), patch, template, classification
                    )
            finally:
                patch.undo()
        print("PASS", template, classification, flush=True)
    (args.output / "walkthrough.json").write_text(
        json.dumps(
            dict(
                id="E56-GUI",
                date=datetime.now(UTC).isoformat(),
                package_root=str(package),
                python=sys.version,
                cases=records,
                limits="Synthetic developer offscreen/software evidence; no human/AT/minimum hardware/clean offline install/GPU claim",
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
