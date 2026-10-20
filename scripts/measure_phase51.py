"""Actual source/installed inspection GUI, safe export and atomic archive walkthrough."""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package-root", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tests"))
    if args.package_root:
        sys.path.insert(0, str(args.package_root.resolve()))
        os.environ["PYTHONPATH"] = str(args.package_root.resolve())
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    import pytest
    import test_explanation_gui as cases
    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest
    from test_unsupervised_gui import visual_find

    import veri_ufku

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = dict(
        id="E51-GUI",
        environment="ENV-51",
        date=datetime.now(UTC).isoformat(),
        package_file=veri_ufku.__file__,
        cases=[],
        controls=[],
    )

    def capture(app, window, projects, c, method, export):
        folder = output / method
        folder.mkdir(exist_ok=True)
        full = folder / "explanation.json"
        full.write_text(
            json.dumps(c.explanation, ensure_ascii=False, allow_nan=False, indent=2)
            + "\n"
        )
        masked = folder / "masked-export.json"
        masked.write_bytes(export.read_bytes())
        images = []
        for width, height in ((1366, 900), (1000, 720)):
            window.setWidth(width)
            window.setHeight(height)
            for name in (
                "explanationMethod",
                "explanationScope",
                {
                    "local-linear": "explanationLocal",
                    "fairness": "explanationFairness",
                    "pdp": "explanationPDP",
                    "ice": "explanationPDP",
                    "what-if": "explanationScenario",
                    "constrained": "explanationScenario",
                }.get(method, "explanationScope"),
            ):
                item = window.findChild(QObject, name) or visual_find(
                    window.contentItem(), name
                )
                assert item is not None
                parent = item.parentItem()
                while parent is not None:
                    if parent.property("contentY") is not None:
                        position = item.mapToItem(parent.property("contentItem"), 0, 0)
                        parent.setProperty("contentY", max(0, position.y() - 20))
                        break
                    parent = parent.parentItem()
                QTest.qWait(100)
                target = folder / (name + "-" + str(width) + ".png")
                assert window.grabWindow().save(str(target))
                images.append(str(target.relative_to(output)))
        p = c.explanation["provenance"]
        report["cases"].append(
            dict(
                method=method,
                status="passed",
                n=p["n"],
                eligible_n=p["eligible_n"],
                background_n=p["background_n"],
                fit_calls=p["fit_calls"],
                prediction_calls=p["prediction_calls"],
                prediction_row_passes=p["prediction_row_passes"],
                scope=p["scope"],
                screenshots=list(dict.fromkeys(images)),
                artifacts=[
                    dict(
                        path=str(path.relative_to(output)),
                        bytes=path.stat().st_size,
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    )
                    for path in (full, masked)
                ],
            )
        )
        (output / "walkthrough.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )

    cases.CAPTURE = capture
    for method in cases.CASES:
        with (
            tempfile.TemporaryDirectory(prefix="veri-ufku-f51-") as t,
            pytest.MonkeyPatch.context() as patch,
        ):
            cases.test_actual_inspection_gui_save_export_mask_reopen(
                Path(t), patch, method
            )
        print("PASS", method, flush=True)
    with (
        tempfile.TemporaryDirectory(prefix="veri-ufku-f51-cancel-") as t,
        pytest.MonkeyPatch.context() as patch,
    ):
        cases.test_optional_disabled_and_cancel_preserves_saved_explanation(
            Path(t), patch
        )
    report["controls"].append(
        dict(
            path="cancel/optional-unavailable/no-overwrite",
            status="passed",
            optional_backend="SHAP unavailable; computation NOT validated",
        )
    )
    (output / "walkthrough.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print("PASS cancel/optional-unavailable/no-overwrite", flush=True)


if __name__ == "__main__":
    main()
