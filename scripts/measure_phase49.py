"""Source/installed real search controls, JSON export, curves, test ledger and reopening."""

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
    import test_search_gui as cases
    from PySide6.QtCore import QObject
    from PySide6.QtTest import QTest
    from test_unsupervised_gui import visual_find

    import veri_ufku

    if args.package_root:
        assert Path(veri_ufku.__file__).is_relative_to(args.package_root.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = dict(
        id="E49-GUI",
        environment="ENV-49",
        date=datetime.now(UTC).isoformat(),
        package_file=veri_ufku.__file__,
        cases=[],
        controls=[],
    )

    def capture(app, window, c, method, structure, purpose, projects):
        folder = output / (method + "-" + structure + "-" + purpose)
        folder.mkdir(exist_ok=True)
        (folder / "search.json").write_text(
            json.dumps(c.result, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        )
        journal = [
            r
            for r in projects.draft["results"]
            if "test_use" in r or "model_choice" in r
        ]
        (folder / "journal.json").write_text(
            json.dumps(journal, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        )
        artifacts = [
            dict(
                path=str(p.relative_to(output)),
                bytes=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            )
            for p in (folder / "search.json", folder / "journal.json")
        ]
        images = []
        for width, height in ((1366, 900), (1000, 720)):
            window.setWidth(width)
            window.setHeight(height)
            for name in (
                "searchMethod",
                "searchCost",
                "searchHistory",
                "searchLearningCurve",
                "searchValidationCurve",
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
        report["cases"].append(
            dict(
                method=method,
                structure=structure,
                purpose=purpose,
                status=c.result["status"],
                trial_count=len(c.result["trials"]),
                outer_count=len(c.result["outer_evaluations"]),
                native_fit_reservations=c.result["native_fit_reservations"],
                prior_test_use_ids=c.result["prior_test_use_ids"],
                screenshots=images,
                artifacts=artifacts,
            )
        )
        (output / "walkthrough.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )

    cases.CAPTURE = capture
    for method, structure, purpose in cases.CASES:
        with (
            tempfile.TemporaryDirectory(prefix="veri-ufku-f49-") as t,
            pytest.MonkeyPatch.context() as patch,
        ):
            cases.test_real_search_controls_and_model_handoff(
                Path(t), patch, method, structure, purpose
            )
        print("PASS", method, structure, purpose, flush=True)
    for structure in ("independent", "group_time"):
        with (
            tempfile.TemporaryDirectory(prefix="veri-ufku-f49-resume-") as t,
            pytest.MonkeyPatch.context() as patch,
        ):
            cases.test_real_cancel_resume_preserves_previous_result_and_optional_disabled(
                Path(t), patch, structure
            )
        report["controls"].append(
            dict(
                path="cancel/resume/optional-disabled",
                structure=structure,
                status="passed",
            )
        )
        print("PASS cancel/resume", structure, flush=True)
    with (
        tempfile.TemporaryDirectory(prefix="veri-ufku-f49-early-") as t,
        pytest.MonkeyPatch.context() as patch,
    ):
        cases.test_real_early_stopping_and_pruning_controls(Path(t), patch)
    report["controls"].append(
        dict(path="external early stopping/pruning", status="passed")
    )
    (output / "walkthrough.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print("PASS early/prune", flush=True)


if __name__ == "__main__":
    main()
