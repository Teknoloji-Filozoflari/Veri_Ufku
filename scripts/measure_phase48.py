"""Phase48 real source/installed QML train/evaluate/predict and safe artifact evidence."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package-root", type=Path)
    parser.add_argument(
        "--case", action="append", help="METHOD:PURPOSE; affected-case replay"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tests"))
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    import pytest
    import test_model_families_gui as cases
    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest
    from test_unsupervised_gui import visual_find

    import veri_ufku

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = dict(
        id="E48-GUI",
        environment="ENV-48",
        date=datetime.now(UTC).isoformat(),
        package_file=veri_ufku.__file__,
        cases=[],
    )
    pending = {}

    def capture(
        app, window, validation, lifecycle, method, purpose, prediction, record
    ):
        folder = output / (method + "-" + purpose)
        folder.mkdir(exist_ok=True)
        if prediction is None:
            pending[(method, purpose)] = dict(
                method=method,
                purpose=purpose,
                screenshots=[],
                artifacts=[],
                current_at_training=validation.current,
                fit_scope=record["baseline"]["model_card"]["fit_row_ids"],
            )
            names = ("familyMethod", "familyCost", "familyDiagnostics")
        else:
            names = ("lifecycleOutputPath",)
            (folder / "result.json").write_text(
                json.dumps(
                    record["baseline"], ensure_ascii=False, allow_nan=False, indent=2
                )
                + "\n"
            )
            (folder / "model-card.json").write_text(
                json.dumps(
                    lifecycle.card, ensure_ascii=False, allow_nan=False, indent=2
                )
                + "\n"
            )
            shutil.copyfile(prediction, folder / "prediction.parquet")
        value = pending[(method, purpose)]
        for width, height in ((1366, 900), (1000, 720)):
            window.setWidth(width)
            window.setHeight(height)
            for name in names:
                item = window.findChild(QObject, name) or visual_find(
                    window.contentItem(), name
                )
                assert item is not None
                container = item.parentItem()
                while container is not None:
                    if container.property("contentY") is not None:
                        position = item.mapToItem(
                            container.property("contentItem"), 0, 0
                        )
                        container.setProperty("contentY", max(0, position.y() - 25))
                        break
                    container = container.parentItem()
                QTest.qWait(100)
                target = folder / (name + "-" + str(width) + ".png")
                assert window.grabWindow().save(str(target))
                value["screenshots"].append(str(target.relative_to(output)))
        if prediction is not None:
            for name in ("result.json", "model-card.json", "prediction.parquet"):
                p = folder / name
                value["artifacts"].append(
                    dict(
                        path=str(p.relative_to(output)),
                        bytes=p.stat().st_size,
                        sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                    )
                )
            value["prediction"] = lifecycle.outputReport
            report["cases"].append(value)
            (output / "walkthrough.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            )

    cases.CAPTURE = capture
    selected = (
        cases.CASES
        if not args.case
        else [tuple(value.split(":")) for value in args.case]
    )
    assert all(value in cases.CASES for value in selected)
    for method, purpose in selected:
        with (
            tempfile.TemporaryDirectory(prefix="veri-ufku-f48-") as t,
            pytest.MonkeyPatch.context() as patch,
        ):
            cases.test_family_gui_train_evaluate_predict(
                Path(t), patch, method, purpose
            )
        print("PASS", method, purpose, flush=True)


if __name__ == "__main__":
    main()
